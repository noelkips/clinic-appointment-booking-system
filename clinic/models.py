from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q, F
from django.utils import timezone

class Doctor(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='doctor_profile')
    specialty = models.CharField(max_length=120)
    is_available = models.BooleanField(default=True)
    biography = models.TextField(blank=True)
    def __str__(self): return f'Dr. {self.user.get_full_name() or self.user.username}'

class Patient(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='patient_profile')
    phone = models.CharField(max_length=40, blank=True)
    def __str__(self): return self.user.get_full_name() or self.user.username

class DoctorAvailability(models.Model):
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='availability')
    weekday = models.PositiveSmallIntegerField()  # Monday=0
    start_time = models.TimeField()
    end_time = models.TimeField()
    slot_minutes = models.PositiveSmallIntegerField(default=30)
    class Meta:
        ordering = ['doctor', 'weekday', 'start_time']
        constraints = [
            models.CheckConstraint(condition=Q(weekday__lte=6), name='valid_weekday'),
            models.CheckConstraint(condition=Q(end_time__gt=F('start_time')), name='schedule_positive_period'),
            models.CheckConstraint(condition=Q(slot_minutes=30), name='thirty_minute_slots'),
            models.UniqueConstraint(fields=['doctor', 'weekday', 'start_time'], name='unique_schedule_start'),
        ]

    def clean(self):
        if self.weekday is None or not 0 <= self.weekday <= 6:
            raise ValidationError('Choose a valid weekday.')
        if self.start_time is None or self.end_time is None:
            raise ValidationError('Provide both the start and end of the working period.')
        if self.slot_minutes != 30 or self.start_time >= self.end_time:
            raise ValidationError('Use 30-minute slots and a start before the end.')
        if self.doctor_id and DoctorAvailability.objects.filter(doctor_id=self.doctor_id, weekday=self.weekday, start_time__lt=self.end_time, end_time__gt=self.start_time).exclude(pk=self.pk).exists():
            raise ValidationError('Working periods cannot overlap.')

    def __str__(self):
        return f'{self.doctor} · {self.weekday} · {self.start_time}–{self.end_time}'

class Appointment(models.Model):
    class Status(models.TextChoices): CONFIRMED='confirmed','Confirmed'; CANCELLED='cancelled','Cancelled'
    patient = models.ForeignKey(Patient, on_delete=models.PROTECT, related_name='appointments')
    doctor = models.ForeignKey(Doctor, on_delete=models.PROTECT, related_name='appointments')
    starts_at = models.DateTimeField()
    reason = models.CharField(max_length=200, blank=True)
    cancellation_reason = models.CharField(max_length=500, blank=True, default='')
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.CONFIRMED)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ['starts_at']
        constraints = [models.UniqueConstraint(fields=['doctor','starts_at'], condition=models.Q(status='confirmed'), name='unique_confirmed_doctor_slot'), models.UniqueConstraint(fields=['patient','starts_at'], condition=models.Q(status='confirmed'), name='unique_confirmed_patient_slot')]
    def clean(self):
        from .services import validate_slot
        if self.starts_at and self.doctor_id:
            validate_slot(self.doctor, self.starts_at, self.patient_id, self.pk)


class AppointmentEvent(models.Model):
    appointment = models.ForeignKey(Appointment, on_delete=models.CASCADE, related_name='events')
    actor = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    action = models.CharField(max_length=20, choices=[('booked', 'Booked'), ('cancelled', 'Cancelled'), ('rescheduled', 'Rescheduled')])
    occurred_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-occurred_at', '-pk']
