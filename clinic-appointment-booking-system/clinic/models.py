from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models

class Doctor(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='doctor_profile')
    specialty = models.CharField(max_length=120)
    is_available = models.BooleanField(default=True)
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
    class Meta: unique_together = ('doctor', 'weekday')

class Appointment(models.Model):
    class Status(models.TextChoices): CONFIRMED='confirmed','Confirmed'; CANCELLED='cancelled','Cancelled'
    patient = models.ForeignKey(Patient, on_delete=models.PROTECT, related_name='appointments')
    doctor = models.ForeignKey(Doctor, on_delete=models.PROTECT, related_name='appointments')
    starts_at = models.DateTimeField()
    reason = models.CharField(max_length=200, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.CONFIRMED)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ['starts_at']
        constraints = [models.UniqueConstraint(fields=['doctor','starts_at'], condition=models.Q(status='confirmed'), name='unique_confirmed_doctor_slot'), models.UniqueConstraint(fields=['patient','starts_at'], condition=models.Q(status='confirmed'), name='unique_confirmed_patient_slot')]
    def clean(self):
        from django.utils import timezone
        if self.starts_at <= timezone.now() + timezone.timedelta(hours=1): raise ValidationError('Appointments must be booked at least one hour in advance.')
