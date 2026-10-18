from datetime import datetime, timedelta
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import Appointment, Doctor

class AppointmentSerializer(serializers.ModelSerializer):
    class Meta: model = Appointment; fields = ('id','patient','doctor','starts_at','reason','status','created_at'); read_only_fields=('patient','status','created_at')

@api_view(['POST'])
def create_appointment(request):
    if not hasattr(request.user, 'patient_profile'): return Response({'detail':'Patient profile required.'}, status=403)
    doctor_id = request.data.get('doctor')
    starts_at = request.data.get('starts_at')
    if doctor_id and starts_at and Appointment.objects.filter(doctor_id=doctor_id, starts_at=starts_at, status=Appointment.Status.CONFIRMED).exists():
        return Response({'detail': 'That appointment slot is already booked.'}, status=409)
    serializer = AppointmentSerializer(data=request.data)
    if not serializer.is_valid(): return Response(serializer.errors, status=400)
    try:
        with transaction.atomic():
            appointment = serializer.save(patient=request.user.patient_profile)
            appointment.full_clean(); appointment.save()
    except Exception as exc:
        return Response({'detail': str(exc) or 'Slot unavailable.'}, status=409)
    return Response(AppointmentSerializer(appointment).data, status=201)

@api_view(['GET'])
def availability(request, pk):
    doctor = get_object_or_404(Doctor, pk=pk)
    date_value = request.query_params.get('date')
    if not date_value: return Response({'detail':'date query parameter is required.'}, status=400)
    try: day = datetime.strptime(date_value, '%Y-%m-%d').date()
    except ValueError: return Response({'detail':'Use YYYY-MM-DD.'}, status=400)
    config = doctor.availability.filter(weekday=day.weekday()).first()
    if not config: return Response({'date': date_value, 'slots': []})
    start = datetime.combine(day, config.start_time); end = datetime.combine(day, config.end_time)
    existing = set(doctor.appointments.filter(starts_at__date=day, status=Appointment.Status.CONFIRMED).values_list('starts_at', flat=True))
    slots=[]; cursor=start
    while cursor < end:
        aware=timezone.make_aware(cursor)
        if aware > timezone.now()+timedelta(hours=1) and aware not in existing: slots.append(aware.isoformat())
        cursor += timedelta(minutes=config.slot_minutes)
    return Response({'date': date_value, 'slots': slots})

@api_view(['PATCH'])
def cancel_appointment(request, pk):
    appointment=get_object_or_404(Appointment, pk=pk)
    if not (request.user.is_staff or getattr(request.user,'patient_profile',None)==appointment.patient or getattr(request.user,'doctor_profile',None)==appointment.doctor): return Response({'detail':'Forbidden.'}, status=403)
    appointment.status=Appointment.Status.CANCELLED; appointment.save(update_fields=['status']); return Response(AppointmentSerializer(appointment).data)

@api_view(['PATCH'])
def reschedule_appointment(request, pk):
    appointment=get_object_or_404(Appointment, pk=pk)
    if getattr(request.user,'patient_profile',None)!=appointment.patient and not request.user.is_staff: return Response({'detail':'Forbidden.'}, status=403)
    value=request.data.get('starts_at')
    try: starts=timezone.make_aware(datetime.fromisoformat(value))
    except (TypeError, ValueError): return Response({'detail':'starts_at must be ISO formatted.'}, status=400)
    appointment.starts_at=starts
    try: appointment.full_clean(); appointment.save(update_fields=['starts_at'])
    except Exception as exc: return Response({'detail':str(exc)}, status=409)
    return Response(AppointmentSerializer(appointment).data)

@api_view(['GET'])
def patient_appointments(request, pk):
    if not request.user.is_staff and getattr(request.user,'patient_profile',None) and request.user.patient_profile.pk != pk: return Response({'detail':'Forbidden.'}, status=403)
    return Response(AppointmentSerializer(Appointment.objects.filter(patient_id=pk), many=True).data)
