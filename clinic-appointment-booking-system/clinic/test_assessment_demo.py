import io,os,secrets
from unittest.mock import patch
from django.test import TestCase
from django.core.management import call_command
from django.core.management.base import CommandError
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import datetime, time, timedelta
from .services import available_slots, book_appointment, change_appointment, SlotConflict
from .models import Doctor,Patient,Appointment,AppointmentEvent
from .management.commands.seed_assessment_demo import GROUP

class AssessmentDemoTests(TestCase):
    def setUp(self):
        self.passwords={f'ASSESSMENT_{kind}_PASSWORD':secrets.token_urlsafe(32) for kind in ('ADMINISTRATOR','DOCTOR','PATIENT')}
        self.scope=patch.dict(os.environ,dict(self.passwords,ASSESSMENT_DEMO_ENABLED='True'))
        self.scope.start();self.addCleanup(self.scope.stop)
        from django.db import connection
        self.database=connection.settings_dict['NAME']
    def seed(self,**kwargs):
        output=io.StringIO()
        call_command('seed_assessment_demo',confirm_database=self.database,stdout=output,**kwargs)
        self.assertTrue(all(value not in output.getvalue() for value in self.passwords.values()))
    def test_dataset_and_idempotency(self):
        unrelated=User.objects.create_user('unrelated',password='unrelated-fixture-password')
        self.seed()
        self.assertEqual(Doctor.objects.count(),5);self.assertEqual(Patient.objects.count(),20)
        self.assertEqual(Appointment.objects.count(),100)
        self.assertEqual(Appointment.objects.filter(status='cancelled').count(),15)
        self.assertTrue(AppointmentEvent.objects.filter(action='rescheduled').exists())
        self.assertTrue(Appointment.objects.filter(starts_at__lt=timezone.now()).exists())
        self.assertTrue(Appointment.objects.filter(starts_at__gt=timezone.now()).exists())
        admin=User.objects.get(username='demo_admin')
        self.assertTrue(admin.is_staff);self.assertFalse(admin.is_superuser)
        self.assertFalse(admin.user_permissions.exists())
        for kind,name in [('ADMINISTRATOR','demo_admin'),('DOCTOR','demo_doctor'),('PATIENT','demo_patient')]:
            self.assertTrue(self.client.login(username=name,password=self.passwords['ASSESSMENT_'+kind+'_PASSWORD']))
            self.client.logout()
        before=list(Appointment.objects.values());hashes=list(User.objects.values_list('pk','password'))
        self.seed()
        self.assertEqual(before,list(Appointment.objects.values()))
        self.assertEqual(hashes,list(User.objects.values_list('pk','password')))
        unrelated.refresh_from_db();self.assertTrue(unrelated.check_password('unrelated-fixture-password'))
    def test_name_collision_rolls_back_everything(self):
        User.objects.create_user('demo_patient')
        with self.assertRaises(CommandError):self.seed()
        self.assertEqual(User.objects.count(),1);self.assertFalse(Doctor.objects.exists())
    def test_explicit_target_and_flag_required(self):
        with self.assertRaises(CommandError):call_command('seed_assessment_demo',confirm_database='wrong')
        with patch.dict(os.environ,{'ASSESSMENT_DEMO_ENABLED':'False'}):
            with self.assertRaises(CommandError):self.seed()
        self.assertFalse(User.objects.exists())
    def test_shared_or_short_passwords_rejected(self):
        with patch.dict(os.environ,{'ASSESSMENT_DOCTOR_PASSWORD':self.passwords['ASSESSMENT_PATIENT_PASSWORD']}):
            with self.assertRaises(CommandError):self.seed()
        self.assertFalse(User.objects.exists())
    def test_inspection_is_read_only(self):
        call_command('seed_assessment_demo',inspect=True,stdout=io.StringIO())
        self.assertFalse(User.objects.exists())
    def test_explicit_rotation_preserves_records(self):
        self.seed();before=list(Appointment.objects.values());events=AppointmentEvent.objects.count()
        with patch.dict(os.environ,{'ASSESSMENT_PATIENT_PASSWORD':secrets.token_urlsafe(32)}):
            with self.assertRaises(CommandError):self.seed()
            self.seed(rotate_passwords=True)
        self.assertEqual(before,list(Appointment.objects.values()));self.assertEqual(events,AppointmentEvent.objects.count())
    def test_rotation_never_creates_missing_accounts(self):
        with self.assertRaises(CommandError):self.seed(rotate_passwords=True)
        self.assertFalse(User.objects.exists())
    def test_designated_records_support_booking_rescheduling_and_cancellation(self):
        self.seed()
        user=User.objects.get(username='demo_patient')
        doctor=User.objects.get(username='demo_doctor').doctor_profile
        day=timezone.localdate()+timedelta(days=35)
        while day.weekday()>4:day+=timedelta(days=1)
        slots=available_slots(doctor,day)
        self.assertGreater(len(slots),2)
        obj=book_appointment(user,doctor,slots[0])
        with self.assertRaises(SlotConflict):book_appointment(user,doctor,slots[0])
        change_appointment(user,obj.pk,'rescheduled',slots[1])
        self.assertIn(slots[0],available_slots(doctor,day))
        change_appointment(user,obj.pk,'cancelled',cancellation_reason='Disposable assessment verification')
        self.assertIn(slots[1],available_slots(doctor,day))
