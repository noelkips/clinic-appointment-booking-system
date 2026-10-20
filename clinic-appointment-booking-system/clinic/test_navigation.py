import os
from unittest.mock import patch
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from . import tests as booking_tests
from .demo import rotate_passwords, DEMO_USERNAMES, DEMO_GROUP
from .models import Appointment, Doctor, DoctorAvailability, Patient, AppointmentEvent

class NavigationTests(TestCase):
    setUpTestData=classmethod(booking_tests.ClinicTests.setUpTestData.__func__)
    def test_role_menus_and_destinations(self):
        cases=[(self.admin,'/platform/',['Overview','Appointments','Doctors','Patients','Working schedules','Activity','Account']),
               (self.doctor_user,'/doctor-dashboard/',['Dashboard','My appointments','My schedule','Account']),
               (self.patient_user,'/dashboard/',['Dashboard','Find doctors','Book appointment','My appointments','Account'])]
        for user,url,labels in cases:
            self.client.force_login(user)
            response=self.client.get(url)
            self.assertEqual([item['label'] for item in response.context['navigation_items']],labels)
            for item in response.context['navigation_items']:
                with self.subTest(role=user.username,url=item['url']):self.assertEqual(self.client.get(item['url']).status_code,200)
            self.assertNotContains(response,'href="/django-admin/"')
    def test_nested_active_doctor(self):
        self.client.force_login(self.admin)
        r=self.client.get(f'/platform/doctors/{self.doctor.pk}/')
        self.assertEqual([x['label'] for x in r.context['navigation_items'] if x['active']],['Doctors'])
        self.assertEqual(r.context['navigation_title'],'Doctor profile')
        self.assertEqual(r.context['navigation_parent']['url'],'/platform/doctors/')
    def test_nested_active_patient(self):
        self.client.force_login(self.admin)
        r=self.client.get(f'/platform/patients/{self.patient.pk}/')
        self.assertEqual([x['label'] for x in r.context['navigation_items'] if x['active']],['Patients'])
    def test_active_overview_is_exact(self):
        self.client.force_login(self.admin)
        for path,label in [('/platform/','Overview'),('/platform/appointments/','Appointments'),('/platform/schedules/','Working schedules'),('/account/','Account')]:
            r=self.client.get(path)
            self.assertEqual([x['label'] for x in r.context['navigation_items'] if x['active']],[label])
    def test_public_nested_doctor_active(self):
        r=self.client.get(f'/doctors/{self.doctor.pk}/')
        self.assertTrue(r.context['public_doctors_active']);self.assertFalse(r.context['public_home_active'])
    def test_shared_navigation_components(self):
        self.assertTemplateUsed(self.client.get('/'),'components/public_header.html')
        self.assertTemplateUsed(self.client.get('/accounts/login/'),'components/brand.html')
        self.client.force_login(self.patient_user)
        r=self.client.get('/dashboard/')
        for template in ['components/dashboard_sidebar.html','components/dashboard_header.html','components/user_menu.html','components/mobile_navigation.html','components/breadcrumbs.html']:
            self.assertTemplateUsed(r,template)
    def test_public_account_actions_and_active_routes(self):
        for user in [None, self.patient_user, self.doctor_user, self.admin]:
            self.client.logout()
            if user:
                self.client.force_login(user)
            for path in ['/', '/doctors/', f'/doctors/{self.doctor.pk}/']:
                with self.subTest(user=user, path=path):
                    response = self.client.get(path)
                    self.assertTemplateUsed(response, 'components/public_header.html')
                    self.assertContains(response, 'data-nav-breakpoint="1119px"')
                    self.assertContains(response, 'aria-controls="public-navigation"')
                    if user:
                        self.assertContains(response, 'My Workspace')
                        self.assertContains(response, 'My Account')
                        self.assertEqual(self.client.get(response.context['workspace_url']).status_code, 200)
                    else:
                        self.assertContains(response, 'Book an Appointment')
                        self.assertContains(response, 'href="/appointments/book/"')
                        self.assertRedirects(self.client.get('/appointments/book/'), '/accounts/login/?next=/appointments/book/')
                        self.assertContains(response, 'Sign In')
                    self.assertEqual(response.context['public_home_active'], path == '/')
                    self.assertEqual(response.context['public_doctors_active'], path.startswith('/doctors/'))

    def test_doctor_schedule_is_scoped_and_guarded(self):
        self.client.force_login(self.doctor_user)
        r=self.client.get('/doctor-dashboard/schedule/')
        self.assertEqual(r.status_code,200)
        self.assertTrue(all(period.doctor_id==self.doctor.pk for period in r.context['periods']))
        for user in [self.patient_user,self.admin]:
            self.client.force_login(user)
            self.assertEqual(self.client.get('/doctor-dashboard/schedule/').status_code,403)
        self.client.logout();self.assertEqual(self.client.get('/doctor-dashboard/schedule/').status_code,302)
    def test_logout_uses_post(self):
        self.client.force_login(self.patient_user)
        self.assertEqual(self.client.get('/accounts/logout/').status_code,405)
        self.assertRedirects(self.client.post('/accounts/logout/'),'/')

@override_settings(DEBUG=True,DEMO_SEED_ENABLED=True)
class DemoRotationTests(TestCase):
    def setUp(self):
        with patch.dict(os.environ,{'DEMO_PASSWORD':'clinic-test-before'}):
            call_command('seed_demo',no_reference=True,verbosity=0)
        self.real=User.objects.create_user('unrelated',password='unrelated-test-secret')
    def snapshot(self):
        return {model.__name__:list(model.objects.order_by('pk').values()) for model in [Doctor,Patient,DoctorAvailability,Appointment,AppointmentEvent]}
    def test_rotation_authenticates_and_preserves_data(self):
        before=self.snapshot();real_hash=self.real.password
        users=rotate_passwords('clinic-test-after','clinic-test-before')
        self.assertEqual(len(users),27)
        for u in users:
            self.assertIsNotNone(authenticate(username=u.username,password='clinic-test-after'))
            self.assertIsNone(authenticate(username=u.username,password='clinic-test-before'))
        self.assertEqual(before,self.snapshot());self.real.refresh_from_db();self.assertEqual(self.real.password,real_hash)
        self.assertEqual(User.objects.count(),28)
    def test_ambiguous_admin_aborts_entire_rotation(self):
        admin=User.objects.get(username='admin');admin.groups.clear()
        before=list(User.objects.order_by('pk').values_list('password',flat=True))
        with self.assertRaises(CommandError):rotate_passwords('clinic-test-after')
        self.assertEqual(before,list(User.objects.order_by('pk').values_list('password',flat=True)))
    def test_missing_user_aborts(self):
        User.objects.get(username='admin2').delete()
        with self.assertRaises(CommandError):rotate_passwords('clinic-test-after')
    @override_settings(DEBUG=False)
    def test_production_refused(self):
        with self.assertRaises(CommandError):rotate_passwords('clinic-test-after')
    @override_settings(DEMO_SEED_ENABLED=False)
    def test_explicit_local_opt_in_required(self):
        with self.assertRaises(CommandError):rotate_passwords('clinic-test-after')
    def test_passwords_only_requires_reset_flag(self):
        with self.assertRaises(CommandError):call_command('seed_demo',passwords_only=True,no_reference=True)
    def test_password_only_command_preserves_dataset(self):
        before=self.snapshot()
        with patch.dict(os.environ,{'DEMO_PASSWORD':'clinic-test-after','DEMO_PREVIOUS_PASSWORD':'clinic-test-before'}):
            call_command('seed_demo',reset_passwords=True,passwords_only=True,no_reference=True)
        self.assertEqual(before,self.snapshot())
    def test_ordinary_seed_does_not_reset_hashes(self):
        before=list(User.objects.filter(username__in=DEMO_USERNAMES).order_by('pk').values_list('password',flat=True))
        with patch.dict(os.environ,{'DEMO_PASSWORD':'clinic-test-before'}):call_command('seed_demo',no_reference=True,verbosity=0)
        self.assertEqual(before,list(User.objects.filter(username__in=DEMO_USERNAMES).order_by('pk').values_list('password',flat=True)))
