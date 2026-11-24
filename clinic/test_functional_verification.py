from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase

from .models import Doctor
from .services import available_slots


class AvailabilityBoundaryTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username='boundary-doctor')
        cls.doctor = Doctor.objects.create(user=cls.user, specialty='General')

    def test_final_representable_day_has_no_slots(self):
        self.assertEqual(available_slots(self.doctor, date.max), [])

    def test_public_profile_handles_final_day(self):
        response = self.client.get(f'/doctors/{self.doctor.pk}/', {'date': '9999-12-31'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['slots'], [])

    def test_api_handles_final_day(self):
        self.client.force_login(self.user)
        for prefix in ('', '/api'):
            with self.subTest(prefix=prefix):
                response = self.client.get(
                    f'{prefix}/doctors/{self.doctor.pk}/availability', {'date': '9999-12-31'}
                )
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json(), {'date': '9999-12-31', 'slots': []})
