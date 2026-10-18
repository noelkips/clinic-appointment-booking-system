from datetime import date
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError
from django.shortcuts import get_object_or_404
from rest_framework import serializers
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import Appointment, Doctor
from .services import available_slots, book_appointment, change_appointment, role, SlotConflict

class AppointmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Appointment
        fields = ('id', 'patient', 'doctor', 'starts_at', 'reason', 'status', 'created_at')
        read_only_fields = ('patient', 'status', 'created_at')
        validators = []  # The locked service returns conflicts consistently as HTTP 409.

def mutation_error(exc):
    if isinstance(exc, PermissionDenied):
        return Response({'detail': 'Forbidden.'}, status=403)
    if isinstance(exc, Appointment.DoesNotExist):
        return Response({'detail': 'Appointment not found.'}, status=404)
    if isinstance(exc, IntegrityError):
        return Response({'detail': 'That slot is no longer available.'}, status=409)
    return Response({'detail': exc.messages}, status=409 if isinstance(exc, SlotConflict) else 400)

@api_view(['POST'])
def create_appointment(request):
    if role(request.user) != 'patient':
        return Response({'detail': 'Patient profile required.'}, status=403)
    serializer = AppointmentSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=400)
    try:
        obj = book_appointment(request.user, serializer.validated_data['doctor'], serializer.validated_data['starts_at'], serializer.validated_data.get('reason', ''))
    except (ValidationError, PermissionDenied, IntegrityError) as exc:
        return mutation_error(exc)
    return Response(AppointmentSerializer(obj).data, status=201)

@api_view(['GET'])
def availability(request, pk):
    doctor = get_object_or_404(Doctor, pk=pk)
    try:
        day = date.fromisoformat(request.query_params.get('date', ''))
    except ValueError:
        return Response({'detail': 'Provide date as YYYY-MM-DD.'}, status=400)
    return Response({'date': day.isoformat(), 'slots': [s.isoformat() for s in available_slots(doctor, day)]})

@api_view(['PATCH'])
def cancel_appointment(request, pk):
    try:
        obj = change_appointment(request.user, pk, 'cancelled')
    except (ValidationError, PermissionDenied, IntegrityError, Appointment.DoesNotExist) as exc:
        return mutation_error(exc)
    return Response(AppointmentSerializer(obj).data)

@api_view(['PATCH'])
def reschedule_appointment(request, pk):
    try:
        starts = serializers.DateTimeField().run_validation(request.data.get('starts_at'))
    except serializers.ValidationError as exc:
        return Response({'starts_at': exc.detail}, status=400)
    try:
        obj = change_appointment(request.user, pk, 'rescheduled', starts)
    except (ValidationError, PermissionDenied, IntegrityError, Appointment.DoesNotExist) as exc:
        return mutation_error(exc)
    return Response(AppointmentSerializer(obj).data)

@api_view(['GET'])
def patient_appointments(request, pk):
    if role(request.user) != 'administrator' and (role(request.user) != 'patient' or request.user.patient_profile.pk != pk):
        return Response({'detail': 'Forbidden.'}, status=403)
    return Response(AppointmentSerializer(Appointment.objects.filter(patient_id=pk), many=True).data)
