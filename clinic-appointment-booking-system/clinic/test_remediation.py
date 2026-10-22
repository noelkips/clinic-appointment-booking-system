from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta, time
from threading import Barrier
from unittest.mock import patch
import os

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import IntegrityError, connections, transaction
from django.test import TestCase, TransactionTestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from .models import Appointment, AppointmentEvent, Doctor, DoctorAvailability, Patient
from .services import available_slots, book_appointment, change_appointment
from . import tests as booking_tests


class RemediationTests(TestCase):
    setUpTestData = classmethod(booking_tests.ClinicTests.setUpTestData.__func__)

    def api(self, user=None):
        client = APIClient()
        client.force_authenticate(user or self.patient_user)
        return client

    def create(self):
        return book_appointment(self.patient_user, self.doctor, self.start, 'Consultation stays unchanged')

    def shifted_doctor(self):
        doctor = Doctor.objects.create(user=User.objects.create_user('shifted-grid'), specialty='Test')
        DoctorAvailability.objects.create(doctor=doctor, weekday=self.day.weekday(), start_time=time(9,15), end_time=time(12,15))
        return doctor

    def test_cancel_missing_blank_invalid_and_long_reasons_leave_booking_intact(self):
        obj = self.create()
        for body in [{}, {'reason':''}, {'reason':'   '}, {'reason':None}, {'reason':[]}, {'reason':'x'*501}]:
            with self.subTest(body=body):
                response = self.api().patch(f'/appointments/{obj.pk}/cancel', body, format='json')
                self.assertEqual(response.status_code, 400)
                self.assertIn('reason', response.json()['error']['details'])
                obj.refresh_from_db()
                self.assertEqual(obj.status, 'confirmed')
                self.assertEqual(obj.cancellation_reason, '')
        self.assertEqual(AppointmentEvent.objects.filter(appointment=obj).count(), 1)
        self.assertNotIn(self.start, available_slots(self.doctor, self.day))

    def test_cancel_reason_persisted_trimmed_and_repeated_cancel_rejected(self):
        obj = self.create()
        response = self.api().patch(f'/api/appointments/{obj.pk}/cancel', {'reason':'  Travel plans changed  '}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['cancellation_reason'], 'Travel plans changed')
        obj.refresh_from_db()
        self.assertEqual(obj.reason, 'Consultation stays unchanged')
        self.assertEqual(obj.cancellation_reason, 'Travel plans changed')
        self.assertIn(self.start, available_slots(self.doctor, self.day))
        response = self.api().patch(f'/appointments/{obj.pk}/cancel', {'reason':'Another reason'}, format='json')
        self.assertEqual(response.status_code, 400)
        obj.refresh_from_db()
        self.assertEqual(obj.cancellation_reason, 'Travel plans changed')
        self.assertEqual(AppointmentEvent.objects.filter(appointment=obj, action='cancelled').count(), 1)
        self.assertEqual(self.api(self.other_user).post('/appointments', {'doctor':self.doctor.pk, 'starts_at':self.start.isoformat()}, format='json').status_code, 201)

    def test_direct_service_also_requires_reason(self):
        obj = self.create()
        with self.assertRaises(ValidationError):
            change_appointment(self.patient_user, obj.pk, 'cancelled')
        obj.refresh_from_db()
        self.assertEqual(obj.status, 'confirmed')

    def test_html_reason_validation_and_persistence(self):
        obj = self.create()
        self.client.force_login(self.patient_user)
        for reason in ['', '  ', 'x'*501]:
            response = self.client.post(f'/appointments/{obj.pk}/', {'action':'cancelled','reason':reason})
            self.assertEqual(response.status_code, 400)
            self.assertTrue(response.context['cancellation_form'].errors)
            obj.refresh_from_db()
            self.assertEqual(obj.status, 'confirmed')
        response = self.client.post(f'/appointments/{obj.pk}/', {'action':'cancelled','reason':'Family commitment'})
        self.assertEqual(response.status_code, 302)
        self.assertContains(self.client.get(response.url), 'Family commitment')
        obj.refresh_from_db()
        self.assertEqual(obj.cancellation_reason, 'Family commitment')

    def test_cancellation_authorization_with_valid_reason(self):
        obj = self.create()
        for user, code in [(self.other_user,404),(self.doctor_user,403)]:
            self.assertEqual(self.api(user).patch(f'/appointments/{obj.pk}/cancel', {'reason':'Cannot attend'}, format='json').status_code, code)
        self.assertEqual(self.api(self.admin).patch(f'/appointments/{obj.pk}/cancel', {'reason':'Clinic closure'}, format='json').status_code, 200)

    def test_patient_overlap_across_shifted_grids_rejected_and_adjacent_allowed(self):
        self.create()
        second = self.shifted_doctor()
        for minutes, code in [(15,409),(45,201)]:
            response = self.api().post('/appointments', {'doctor':second.pk,'starts_at':(self.start+timedelta(minutes=minutes)).isoformat()}, format='json')
            self.assertEqual(response.status_code, code)

    def test_doctor_shifted_grid_and_availability_exclude_full_overlap(self):
        self.create()
        self.doctor.availability.all().delete()
        DoctorAvailability.objects.create(doctor=self.doctor, weekday=self.day.weekday(), start_time=time(9,15), end_time=time(12,15))
        overlapping = self.start+timedelta(minutes=15)
        self.assertNotIn(overlapping, available_slots(self.doctor, self.day))
        self.assertIn(self.start+timedelta(minutes=45), available_slots(self.doctor, self.day))
        response = self.api(self.other_user).post('/appointments', {'doctor':self.doctor.pk,'starts_at':overlapping.isoformat()}, format='json')
        self.assertEqual(response.status_code, 409)

    def test_availability_checks_previous_day_interval(self):
        midnight = timezone.make_aware(timezone.datetime.combine(self.day, time(0)))
        Appointment.objects.create(doctor=self.doctor, patient=self.other, starts_at=midnight-timedelta(minutes=15))
        self.doctor.availability.all().delete()
        DoctorAvailability.objects.create(doctor=self.doctor, weekday=self.day.weekday(), start_time=time(0), end_time=time(1))
        slots = available_slots(self.doctor, self.day)
        self.assertNotIn(midnight, slots)
        self.assertIn(midnight+timedelta(minutes=30), slots)

    def test_reschedule_patient_overlap_rolls_back_and_old_slot_stays_occupied(self):
        obj = self.create()
        second = self.shifted_doctor()
        other = book_appointment(self.patient_user, second, self.start+timedelta(minutes=75))
        response = self.api().patch(f'/appointments/{other.pk}/reschedule', {'starts_at':(self.start+timedelta(minutes=15)).isoformat()}, format='json')
        self.assertEqual(response.status_code, 409)
        other.refresh_from_db()
        self.assertEqual(other.starts_at, self.start+timedelta(minutes=75))
        self.assertNotIn(other.starts_at, available_slots(second, self.day))

    def test_database_blocks_doctor_and_patient_interval_insert_and_update(self):
        self.create()
        second = self.shifted_doctor()
        for doctor, patient in [(self.doctor,self.other),(second,self.patient)]:
            with self.subTest(doctor=doctor.pk), self.assertRaises(IntegrityError), transaction.atomic():
                Appointment.objects.create(doctor=doctor, patient=patient, starts_at=self.start+timedelta(minutes=15))
        obj = Appointment.objects.create(doctor=second, patient=self.patient, starts_at=self.start+timedelta(minutes=75))
        with self.assertRaises(IntegrityError), transaction.atomic():
            Appointment.objects.filter(pk=obj.pk).update(starts_at=self.start+timedelta(minutes=15))
        # Half-open intervals allow exactly adjacent starts.
        Appointment.objects.create(doctor=self.doctor, patient=self.other, starts_at=self.start+timedelta(minutes=30))

    def test_reschedule_doctor_overlap_after_schedule_shift_rolls_back(self):
        self.create()
        moving = book_appointment(self.other_user, self.doctor, self.start+timedelta(hours=1))
        self.doctor.availability.all().delete()
        DoctorAvailability.objects.create(doctor=self.doctor, weekday=self.day.weekday(), start_time=time(9,15), end_time=time(12,15))
        response = self.api(self.other_user).patch(f'/appointments/{moving.pk}/reschedule', {'starts_at':(self.start+timedelta(minutes=15)).isoformat()}, format='json')
        self.assertEqual(response.status_code, 409)
        moving.refresh_from_db()
        self.assertEqual(moving.starts_at, self.start+timedelta(hours=1))

    def test_bonus_upcoming_filter_sort_and_permissions(self):
        Appointment.objects.create(doctor=self.doctor, patient=self.patient, starts_at=self.start-timedelta(days=14))
        Appointment.objects.create(doctor=self.doctor, patient=self.patient, starts_at=self.start, status='cancelled')
        late = Appointment.objects.create(doctor=self.doctor, patient=self.patient, starts_at=self.start+timedelta(hours=1))
        early = Appointment.objects.create(doctor=self.doctor, patient=self.patient, starts_at=self.start+timedelta(minutes=30))
        Appointment.objects.create(doctor=self.doctor, patient=self.other, starts_at=self.start+timedelta(hours=2))
        for prefix in ['', '/api']:
            for user in [self.patient_user,self.admin]:
                response = self.api(user).get(f'{prefix}/patients/{self.patient.pk}/appointments')
                self.assertEqual([x['id'] for x in response.data], [early.pk,late.pk])
            for user in [self.other_user,self.doctor_user]:
                self.assertEqual(self.api(user).get(f'{prefix}/patients/{self.patient.pk}/appointments').status_code, 403 if user else 401)
        self.assertEqual(APIClient().get(f'/patients/{self.patient.pk}/appointments').status_code, 401)

    def test_one_hour_exact_boundary_and_equivalent_utc_reschedule(self):
        obj = self.create()
        new = self.start+timedelta(minutes=30)
        with patch('django.utils.timezone.now', return_value=new-timedelta(hours=1)):
            response = self.api().patch(f'/appointments/{obj.pk}/reschedule', {'starts_at':new.isoformat()}, format='json')
            self.assertEqual(response.status_code, 400)
        from datetime import timezone as datetime_timezone
        response = self.api().patch(f'/appointments/{obj.pk}/reschedule', {'starts_at':new.astimezone(datetime_timezone.utc).isoformat()}, format='json')
        self.assertEqual(response.status_code, 200)


@override_settings(DEBUG=True, DEMO_SEED_ENABLED=True)
class SeederBoundaryTests(TestCase):
    def test_seed_at_near_notice_boundary_is_idempotent_and_preserves_real_user(self):
        real = User.objects.create_user('real-owner', password='test-unrelated-owner')
        original_hash = real.password
        fixed = timezone.make_aware(timezone.datetime(2026,10,19,9,15))
        with patch('django.utils.timezone.now', return_value=fixed), patch.dict(os.environ, {'DEMO_PASSWORD':'test-demo-boundary-secret'}):
            call_command('seed_demo', no_reference=True, verbosity=0)
            before = list(Appointment.objects.values_list('id','starts_at','status','reason'))
            hashes = list(User.objects.order_by('pk').values_list('password',flat=True))
            call_command('seed_demo', no_reference=True, verbosity=0)
            self.assertEqual(before, list(Appointment.objects.values_list('id','starts_at','status','reason')))
            self.assertEqual(hashes, list(User.objects.order_by('pk').values_list('password',flat=True)))
        self.assertEqual(Appointment.objects.count(),100)
        self.assertTrue(Appointment.objects.filter(starts_at__lt=fixed).exists())
        self.assertFalse(Appointment.objects.filter(starts_at__gte=fixed, starts_at__lte=fixed+timedelta(hours=1)).exists())
        real.refresh_from_db()
        self.assertEqual(real.password, original_hash)
        self.assertFalse(real.is_staff)


class IntervalConcurrencyTests(TransactionTestCase):
    """Run on both supported backends; SQLite may return a safe busy conflict."""
    def test_simultaneous_overlapping_same_patient_requests_have_one_winner(self):
        day = timezone.localdate()+timedelta(days=7)
        start = timezone.make_aware(timezone.datetime.combine(day,time(9)))
        user = User.objects.create_user('concurrent-patient')
        Patient.objects.create(user=user)
        doctors = []
        for i, minute in enumerate([0,15]):
            doc = Doctor.objects.create(user=User.objects.create_user('interval-doc'+str(i)),specialty='Test')
            DoctorAvailability.objects.create(doctor=doc,weekday=day.weekday(),start_time=time(9,minute),end_time=time(12,minute))
            doctors.append(doc.pk)
        barrier = Barrier(2)
        def attempt(index):
            try:
                client = APIClient()
                current = User.objects.get(pk=user.pk)
                # Cache profile before the simultaneous write attempts.
                current.patient_profile
                client.force_authenticate(current)
                barrier.wait(timeout=10)
                return client.post('/appointments', {'doctor':doctors[index], 'starts_at':(start+timedelta(minutes=15*index)).isoformat()}, format='json').status_code
            finally:
                connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool:
            codes = list(pool.map(attempt,[0,1]))
        self.assertEqual(sorted(codes),[201,409])
        self.assertEqual(Appointment.objects.filter(status='confirmed').count(),1)
