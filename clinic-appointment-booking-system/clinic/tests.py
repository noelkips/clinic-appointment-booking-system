from datetime import timedelta
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient
from .models import Appointment, Doctor, DoctorAvailability, Patient

class BookingTests(TestCase):
    def setUp(self):
        self.user=User.objects.create_user('patient', password='pass12345', first_name='Grace'); self.patient=Patient.objects.create(user=self.user)
        self.doctor_user=User.objects.create_user('doctor', password='pass12345', first_name='Jane', last_name='Mwangi'); self.doctor=Doctor.objects.create(user=self.doctor_user, specialty='General practice')
        self.client=APIClient(); self.client.force_authenticate(self.user)
    def test_booking_persists(self):
        start=(timezone.now()+timedelta(days=2)).replace(second=0,microsecond=0).isoformat()
        response=self.client.post('/api/appointments', {'doctor':self.doctor.pk,'starts_at':start,'reason':'Checkup'}, format='json')
        self.assertEqual(response.status_code, 201); self.assertEqual(Appointment.objects.count(), 1)
    def test_double_booking_rejected(self):
        start=timezone.now()+timedelta(days=2)
        Appointment.objects.create(patient=self.patient, doctor=self.doctor, starts_at=start)
        response=self.client.post('/api/appointments', {'doctor':self.doctor.pk,'starts_at':start.isoformat()}, format='json')
        self.assertEqual(response.status_code, 409)
    def test_availability_returns_slots(self):
        future=timezone.localdate()+timedelta(days=7)
        DoctorAvailability.objects.create(doctor=self.doctor, weekday=future.weekday(), start_time='09:00', end_time='10:00')
        response=self.client.get(f'/api/doctors/{self.doctor.pk}/availability?date={future}')
        self.assertEqual(response.status_code, 200); self.assertIn('slots', response.data)
