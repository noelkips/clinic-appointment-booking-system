from datetime import datetime, timedelta
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone
from .models import Appointment, AppointmentEvent, Doctor, Patient


class SlotConflict(ValidationError):
    pass


def role(user):
    if not user.is_authenticated:
        return 'anonymous'
    if user.is_staff:
        return 'administrator'
    if hasattr(user, 'doctor_profile'):
        return 'doctor'
    if hasattr(user, 'patient_profile'):
        return 'patient'
    return 'unassigned'


def visible_appointments(user):
    qs = Appointment.objects.select_related('patient__user', 'doctor__user')
    if role(user) == 'administrator':
        return qs
    if role(user) == 'doctor':
        return qs.filter(doctor=user.doctor_profile)
    if role(user) == 'patient':
        return qs.filter(patient=user.patient_profile)
    return qs.none()


def schedule_matches(doctor, starts):
    local = timezone.localtime(starts)
    for period in doctor.availability.filter(weekday=local.weekday()):
        begin = timezone.make_aware(datetime.combine(local.date(), period.start_time))
        end = timezone.make_aware(datetime.combine(local.date(), period.end_time))
        delta = (starts - begin).total_seconds()
        if begin <= starts and starts + timedelta(minutes=30) <= end and delta % 1800 == 0:
            return True
    return False


def validate_slot(doctor, starts, patient_id=None, exclude=None, historical=False):
    if timezone.is_naive(starts):
        raise ValidationError('Use a timezone-aware appointment time.')
    if not doctor.is_available or not doctor.user.is_active:
        raise ValidationError('This doctor is unavailable.')
    if not historical and starts <= timezone.now() + timedelta(hours=1):
        raise ValidationError('Appointments require more than one hour of advance notice.')
    if not schedule_matches(doctor, starts):
        raise ValidationError('Choose a complete 30-minute slot within working hours.')
    existing = Appointment.objects.filter(status='confirmed', starts_at=starts).exclude(pk=exclude)
    if existing.filter(doctor=doctor).exists() or (patient_id and existing.filter(patient_id=patient_id).exists()):
        raise SlotConflict('This doctor or patient already has an appointment at that time.')


def available_slots(doctor, day):
    if not doctor.is_available or not doctor.user.is_active:
        return []
    booked = set(doctor.appointments.filter(status='confirmed', starts_at__date=day).values_list('starts_at', flat=True))
    slots = []
    for period in doctor.availability.filter(weekday=day.weekday()):
        cursor = timezone.make_aware(datetime.combine(day, period.start_time))
        end = timezone.make_aware(datetime.combine(day, period.end_time))
        while cursor + timedelta(minutes=30) <= end:
            if cursor > timezone.now() + timedelta(hours=1) and cursor not in booked:
                slots.append(cursor)
            cursor += timedelta(minutes=30)
    return sorted(set(slots))


@transaction.atomic
def book_appointment(user, doctor, starts, reason=''):
    if role(user) != 'patient':
        raise PermissionDenied('Patient access required.')
    # Lock the same parent rows for all writes; uniqueness is also enforced in SQL.
    doctor = Doctor.objects.select_for_update().get(pk=doctor.pk)
    patient = Patient.objects.select_for_update().get(pk=user.patient_profile.pk)
    validate_slot(doctor, starts, patient.pk)
    obj = Appointment(patient=patient, doctor=doctor, starts_at=starts, reason=reason)
    obj.full_clean()
    obj.save()
    AppointmentEvent.objects.create(appointment=obj, actor=user, action='booked')
    return obj


@transaction.atomic
def change_appointment(user, pk, action, starts=None):
    original = visible_appointments(user).get(pk=pk)
    if role(user) == 'doctor':
        raise PermissionDenied('Only the patient or an administrator can change this booking.')
    Doctor.objects.select_for_update().get(pk=original.doctor_id)
    Patient.objects.select_for_update().get(pk=original.patient_id)
    obj = Appointment.objects.select_for_update().get(pk=pk)
    if obj.status != 'confirmed' or obj.starts_at <= timezone.now():
        raise ValidationError('Only upcoming confirmed appointments can be changed.')
    if action == 'cancelled':
        obj.status = 'cancelled'
    elif action == 'rescheduled':
        validate_slot(obj.doctor, starts, obj.patient_id, obj.pk)
        obj.starts_at = starts
    else:
        raise ValidationError('Unknown appointment action.')
    obj.save(update_fields=['status', 'starts_at'])
    AppointmentEvent.objects.create(appointment=obj, actor=user, action=action)
    return obj
