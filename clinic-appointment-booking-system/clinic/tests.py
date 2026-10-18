from datetime import timedelta, time
from unittest import skipUnless
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import connection
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient
from .models import Appointment, Doctor, DoctorAvailability, Patient
from .services import available_slots, book_appointment, change_appointment

class ClinicTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.patient_user=User.objects.create_user('patient',password='test-password-274',first_name='Grace')
        cls.patient=Patient.objects.create(user=cls.patient_user)
        cls.other_user=User.objects.create_user('other',password='test-password-274')
        cls.other=Patient.objects.create(user=cls.other_user)
        cls.doctor_user=User.objects.create_user('doctor',password='test-password-274')
        cls.doctor=Doctor.objects.create(user=cls.doctor_user,specialty='General medicine')
        cls.admin=User.objects.create_superuser('admin','admin@example.test','test-password-274')
        cls.day=timezone.localdate()+timedelta(days=7)
        cls.start=timezone.make_aware(timezone.datetime.combine(cls.day,time(9)))
        DoctorAvailability.objects.create(doctor=cls.doctor,weekday=cls.day.weekday(),start_time=time(9),end_time=time(12))
        DoctorAvailability.objects.create(doctor=cls.doctor,weekday=cls.day.weekday(),start_time=time(14),end_time=time(17))
    def api(self,user=None):
        client=APIClient()
        if user: client.force_authenticate(user)
        return client
    def create(self):
        return book_appointment(self.patient_user,self.doctor,self.start,'PRIVATE APPOINTMENT')
    def post(self,start=None,user=None):
        return self.api(user or self.patient_user).post('/api/appointments',{'doctor':self.doctor.pk,'starts_at':(start or self.start).isoformat()},format='json')
    def test_public_pages(self):
        for url in ['/','/doctors/','/accounts/login/','/accounts/register/','/accounts/forgot-password/']:
            with self.subTest(url=url): self.assertEqual(self.client.get(url).status_code,200)
    def test_forgot_password_is_informational(self):
        self.assertContains(self.client.get('/accounts/forgot-password/'),'Password recovery is coming soon')
    def test_login_redirects_by_role(self):
        for user,path in [(self.patient_user,'/dashboard/'),(self.doctor_user,'/doctor-dashboard/'),(self.admin,'/platform/')]:
            with self.subTest(role=user.username):
                self.client.logout()
                self.assertRedirects(self.client.post('/accounts/login/',{'username':user.username,'password':'test-password-274'}),path,fetch_redirect_response=False)
    def test_invalid_credentials(self):
        self.assertContains(self.client.post('/accounts/login/',{'username':'patient','password':'wrong'}),'Please enter a correct')
    def test_unsafe_next_rejected(self):
        response=self.client.post('/accounts/login/?next=https://example.com',{'username':'patient','password':'test-password-274'})
        self.assertEqual(response.url,'/dashboard/')
    def test_forbidden_next_rejected(self):
        response=self.client.post('/accounts/login/?next=/platform/',{'username':'patient','password':'test-password-274'})
        self.assertEqual(response.url,'/dashboard/')
    def test_registration_patient_only(self):
        r=self.client.post('/accounts/register/',{'username':'new','first_name':'New','last_name':'Patient','email':'new@example.test','password1':'patient-test-489','password2':'patient-test-489','is_staff':'true'})
        self.assertEqual(r.status_code,302)
        u=User.objects.get(username='new')
        self.assertFalse(u.is_staff)
        self.assertTrue(hasattr(u,'patient_profile'))
    def test_anonymous_protected(self):
        self.assertEqual(self.client.get('/platform/').status_code,302)
        self.assertEqual(self.api().get(f'/api/patients/{self.patient.pk}/appointments').status_code,403)
    def test_platform_access(self):
        routes=['/platform/','/platform/appointments/','/platform/doctors/','/platform/patients/','/platform/schedules/','/platform/activity/']
        for user,expected in [(self.patient_user,403),(self.doctor_user,403),(self.admin,200)]:
            self.client.force_login(user)
            for url in routes:
                with self.subTest(role=user.username,url=url): self.assertEqual(self.client.get(url).status_code,expected)
    def test_patient_dashboard_isolation(self):
        self.create();self.client.force_login(self.other_user)
        self.assertNotContains(self.client.get('/dashboard/'),'PRIVATE APPOINTMENT')
        self.assertEqual(self.client.get('/dashboard/').context['upcoming_count'],0)
    def test_doctor_dashboard_isolation(self):
        a=self.create()
        other_doc=Doctor.objects.create(user=User.objects.create_user('otherdoc'),specialty='Other')
        Appointment.objects.create(doctor=other_doc,patient=self.other,starts_at=self.start,reason='OTHER PRIVATE')
        self.client.force_login(self.doctor_user)
        r=self.client.get('/doctor-dashboard/')
        self.assertEqual(r.context['upcoming_count'],1)
        self.assertNotContains(r,'OTHER PRIVATE')
    def test_doctor_cannot_read_patient_api(self):
        self.create()
        self.assertEqual(self.api(self.doctor_user).get(f'/api/patients/{self.patient.pk}/appointments').status_code,403)
    def test_patient_cannot_read_other_patient_api(self):
        self.assertEqual(self.api(self.other_user).get(f'/api/patients/{self.patient.pk}/appointments').status_code,403)
    def test_owner_and_admin_can_read_patient_api(self):
        self.create()
        for user in [self.patient_user,self.admin]:
            self.assertEqual(len(self.api(user).get(f'/api/patients/{self.patient.pk}/appointments').data),1)
    def test_booking_persists(self):
        self.assertEqual(self.post().status_code,201)
        self.assertEqual(Appointment.objects.count(),1)
    def test_double_booking_rejected(self):
        self.create();self.assertEqual(self.post(user=self.other_user).status_code,409)
    def test_patient_double_booking_rejected(self):
        self.create()
        doc=Doctor.objects.create(user=User.objects.create_user('second-doctor'),specialty='Test')
        DoctorAvailability.objects.create(doctor=doc,weekday=self.day.weekday(),start_time=time(9),end_time=time(12))
        r=self.api(self.patient_user).post('/api/appointments',{'doctor':doc.pk,'starts_at':self.start.isoformat()},format='json')
        self.assertEqual(r.status_code,409)
    def test_no_hours_rejected(self):
        self.doctor.availability.all().delete();self.assertEqual(self.post().status_code,400)
    def test_gap_rejected(self):
        self.assertEqual(self.post(self.start+timedelta(hours=4)).status_code,400)
    def test_off_grid_rejected(self):
        self.assertEqual(self.post(self.start+timedelta(minutes=15)).status_code,400)
    def test_partial_last_slot_rejected(self):
        self.assertEqual(self.post(self.start+timedelta(hours=7,minutes=45)).status_code,400)
    def test_past_rejected(self):
        self.assertEqual(self.post(self.start-timedelta(days=14)).status_code,400)
    def test_one_hour_rejected(self):
        self.assertEqual(self.post(timezone.now()+timedelta(minutes=30)).status_code,400)
    def test_unavailable_doctor_rejected(self):
        self.doctor.is_available=False;self.doctor.save();self.assertEqual(self.post().status_code,400)
    def test_invalid_doctor_and_timestamp(self):
        for payload in [{'doctor':9999,'starts_at':self.start.isoformat()},{'doctor':self.doctor.pk,'starts_at':'bad'}]:
            self.assertEqual(self.api(self.patient_user).post('/api/appointments',payload,format='json').status_code,400)
    def test_split_availability(self):
        slots=available_slots(self.doctor,self.day)
        self.assertEqual(len(slots),12)
        self.assertNotIn(self.start+timedelta(hours=4),slots)
    def test_availability_returns_slots(self):
        r=self.api(self.patient_user).get(f'/api/doctors/{self.doctor.pk}/availability?date={self.day}')
        self.assertEqual(len(r.data['slots']),12)
    def test_bad_availability_date(self):
        self.assertEqual(self.api(self.patient_user).get(f'/api/doctors/{self.doctor.pk}/availability?date=bad').status_code,400)
    def test_overlap_schedule_rejected(self):
        row=DoctorAvailability(doctor=self.doctor,weekday=self.day.weekday(),start_time=time(10),end_time=time(13))
        with self.assertRaises(ValidationError): row.full_clean()
    def test_missing_schedule_time_is_form_error(self):
        self.client.force_login(self.admin)
        r=self.client.post('/platform/schedules/',{'doctor':self.doctor.pk,'weekday':2,'end_time':'17:00'})
        self.assertEqual(r.status_code,200)
        self.assertIn('start_time',r.context['form'].errors)
    def test_reverse_period_rejected(self):
        row=DoctorAvailability(doctor=self.doctor,weekday=2,start_time=time(14),end_time=time(9))
        with self.assertRaises(ValidationError): row.full_clean()
    def test_cancel_releases_slot(self):
        a=self.create()
        r=self.api(self.patient_user).patch(f'/api/appointments/{a.pk}/cancel',{},format='json')
        self.assertEqual(r.status_code,200)
        self.assertIn(self.start,available_slots(self.doctor,self.day))
    def test_reschedule_aware_releases_old_slot(self):
        a=self.create();new=self.start+timedelta(minutes=30)
        r=self.api(self.patient_user).patch(f'/api/appointments/{a.pk}/reschedule',{'starts_at':new.isoformat()},format='json')
        self.assertEqual(r.status_code,200)
        self.assertIn(self.start,available_slots(self.doctor,self.day))
        self.assertNotIn(new,available_slots(self.doctor,self.day))
    def test_reschedule_gap_rollback(self):
        a=self.create()
        r=self.api(self.patient_user).patch(f'/api/appointments/{a.pk}/reschedule',{'starts_at':(self.start+timedelta(hours=4)).isoformat()},format='json')
        self.assertEqual(r.status_code,400)
        a.refresh_from_db();self.assertEqual(a.starts_at,self.start)
    def test_other_patient_cannot_mutate(self):
        a=self.create()
        self.assertEqual(self.api(self.other_user).patch(f'/api/appointments/{a.pk}/cancel',{},format='json').status_code,404)
    def test_doctor_cannot_mutate(self):
        a=self.create()
        self.assertEqual(self.api(self.doctor_user).patch(f'/api/appointments/{a.pk}/cancel',{},format='json').status_code,403)
    def test_cancelled_cannot_reschedule(self):
        a=self.create();change_appointment(self.patient_user,a.pk,'cancelled')
        self.assertEqual(self.api(self.patient_user).patch(f'/api/appointments/{a.pk}/reschedule',{'starts_at':self.start.isoformat()},format='json').status_code,400)
    def test_root_api_alias(self):
        self.assertEqual(self.api(self.patient_user).post('/appointments',{'doctor':self.doctor.pk,'starts_at':self.start.isoformat()},format='json').status_code,201)
    def test_metrics_and_filtering(self):
        self.create();self.client.force_login(self.admin)
        response=self.client.get('/platform/')
        self.assertEqual(response.context['total_count'],1)
        self.assertEqual(response.context['patients_count'],2)
        self.assertEqual(len(self.client.get('/platform/appointments/?status=cancelled').context['appointments']),0)
    def test_csrf_required(self):
        from django.test import Client
        c=Client(enforce_csrf_checks=True)
        self.assertEqual(c.post('/accounts/login/',{}).status_code,403)

from unittest.mock import patch
from django.test import override_settings, TransactionTestCase
from django.core.management.base import CommandError
from django.db.models import Count
import os

@override_settings(DEBUG=True, DEMO_SEED_ENABLED=True)
class DemoSeedTests(TestCase):
    def seed(self):
        with patch.dict(os.environ, {'DEMO_PASSWORD':'test-demo-password-275'}):
            call_command('seed_demo', no_reference=True, verbosity=0)
    def test_seed_idempotence_authentication_and_counts(self):
        from django.contrib.auth import authenticate
        self.seed();self.seed()
        self.assertEqual(User.objects.count(),27)
        self.assertEqual(User.objects.filter(is_superuser=True).count(),2)
        self.assertEqual(Doctor.objects.count(),5)
        self.assertEqual(Patient.objects.count(),20)
        self.assertEqual(DoctorAvailability.objects.count(),49)
        self.assertEqual(Appointment.objects.count(),100)
        for user in User.objects.all():
            with self.subTest(user=user.username):
                self.assertIsNotNone(authenticate(username=user.username,password='test-demo-password-275'))
                self.client.force_login(user)
                target='/platform/' if user.is_staff else ('/doctor-dashboard/' if hasattr(user,'doctor_profile') else '/dashboard/')
                self.assertEqual(self.client.get(target).status_code,200)
        duplicate=Appointment.objects.filter(status='confirmed').values('doctor','starts_at').annotate(n=Count('id')).filter(n__gt=1)
        self.assertFalse(duplicate.exists())
        duplicate=Appointment.objects.filter(status='confirmed').values('patient','starts_at').annotate(n=Count('id')).filter(n__gt=1)
        self.assertFalse(duplicate.exists())
        for period in DoctorAvailability.objects.all():period.full_clean()
        for appointment in Appointment.objects.all():
            from .services import schedule_matches
            self.assertTrue(schedule_matches(appointment.doctor,appointment.starts_at))
    def test_refuses_unmarked_user_without_changes(self):
        u=User.objects.create_user('admin',password='real-account-password')
        with self.assertRaises(CommandError):self.seed()
        u.refresh_from_db();self.assertFalse(u.is_staff)
        self.assertEqual(User.objects.count(),1)
    @override_settings(DEBUG=False)
    def test_refuses_production(self):
        with self.assertRaises(CommandError):self.seed()
        self.assertEqual(User.objects.count(),0)
    @override_settings(DEMO_SEED_ENABLED=False)
    def test_requires_explicit_opt_in(self):
        with self.assertRaises(CommandError):self.seed()
    def test_password_refresh_requires_deliberate_option(self):
        self.seed()
        with patch.dict(os.environ, {'DEMO_PASSWORD':'different-test-password'}):
            with self.assertRaises(CommandError):call_command('seed_demo',no_reference=True,verbosity=0)
            call_command('seed_demo',no_reference=True,reset_passwords=True,verbosity=0)
        self.assertTrue(User.objects.get(username='patient1').check_password('different-test-password'))

@skipUnless(connection.vendor=='postgresql', 'Requires a real PostgreSQL test database; SQLite cannot verify row locks.')
class PostgreSQLConcurrencyTests(TransactionTestCase):
    def test_concurrent_same_slot_has_one_winner(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier
        from django.db import connections
        from .services import SlotConflict
        doctor=Doctor.objects.create(user=User.objects.create_user('concurrency-doctor'),specialty='General')
        day=timezone.localdate()+timedelta(days=7)
        start=timezone.make_aware(timezone.datetime.combine(day,time(9)))
        DoctorAvailability.objects.create(doctor=doctor,weekday=day.weekday(),start_time=time(9),end_time=time(12))
        users=[]
        for name in ['concurrent-a','concurrent-b']:
            u=User.objects.create_user(name);Patient.objects.create(user=u);users.append(u.pk)
        barrier=Barrier(2)
        def attempt(pk):
            try:
                u=User.objects.get(pk=pk);d=Doctor.objects.get(pk=doctor.pk)
                barrier.wait(timeout=10)
                try:book_appointment(u,d,start);return 'booked'
                except SlotConflict:return 'conflict'
            finally:connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes=list(pool.map(attempt,users))
        self.assertEqual(sorted(outcomes),['booked','conflict'])
        self.assertEqual(Appointment.objects.count(),1)

class ConstraintTests(TestCase):
    setUpTestData = classmethod(ClinicTests.setUpTestData.__func__)
    create = ClinicTests.create
    def test_database_doctor_uniqueness(self):
        from django.db import IntegrityError, transaction
        self.create()
        with self.assertRaises(IntegrityError),transaction.atomic():
            Appointment.objects.create(doctor=self.doctor,patient=self.other,starts_at=self.start)
    def test_api_requires_csrf_for_session_authentication(self):
        from django.test import Client
        c=Client(enforce_csrf_checks=True);c.force_login(self.patient_user)
        self.assertEqual(c.post('/api/appointments',{'doctor':self.doctor.pk,'starts_at':self.start.isoformat()}).status_code,403)

