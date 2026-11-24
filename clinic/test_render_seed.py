import io
import os
import secrets
from pathlib import Path
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
from django.test import TestCase, override_settings
from django.contrib.auth.models import User

from clinic.models import Appointment, Doctor, Patient
from clinic.services import available_slots, book_appointment
from django.utils import timezone
from datetime import timedelta


@override_settings(DEBUG=False)
class RenderSeedTests(TestCase):
    def setUp(self):
        connection.ensure_connection()
        self.env = {
            'RUN_ASSESSMENT_DEMO_SEED': 'true', 'ASSESSMENT_DEMO_ENABLED': 'true',
            'RENDER': 'true', 'DJANGO_SETTINGS_MODULE': 'config.settings',
            'RENDER_SERVICE_ID': 'srv-test', 'ASSESSMENT_EXPECTED_SERVICE_ID': 'srv-test',
            'ASSESSMENT_EXPECTED_DB_HOST': 'dpg-test',
            'ASSESSMENT_EXPECTED_DB_NAME': connection.settings_dict['NAME'],
            'DATABASE_URL': 'postgresql://fixture:private-url-secret@dpg-test/' + connection.settings_dict['NAME'],
            **{'ASSESSMENT_'+kind+'_PASSWORD': secrets.token_urlsafe(32)
               for kind in ('ADMINISTRATOR', 'DOCTOR', 'PATIENT')},
        }
        self.scope = patch.dict(os.environ, self.env)
        self.scope.start(); self.addCleanup(self.scope.stop)
        # Only target metadata is mocked. All writes/constraints use the existing
        # separate PostgreSQL test connection, never a Render connection.
        self.host = patch.dict(connection.settings_dict, {'HOST': 'dpg-test'})
        self.host.start(); self.addCleanup(self.host.stop)

    def run_seed(self):
        output = io.StringIO()
        call_command('run_render_demo_seed', stdout=output)
        for value in list(self.env.values()):
            if value == self.env['DATABASE_URL'] or len(value) > 35:
                self.assertNotIn(value, output.getvalue())
        return output.getvalue()

    def test_disabled_and_both_gates(self):
        with patch.dict(os.environ, {'RUN_ASSESSMENT_DEMO_SEED': 'false'}):
            self.assertIn('disabled', self.run_seed())
        with patch.dict(os.environ, {'ASSESSMENT_DEMO_ENABLED': 'false'}):
            with self.assertRaises(CommandError): self.run_seed()
        self.assertFalse(User.objects.exists())

    def test_missing_credentials_never_prompt(self):
        with patch.dict(os.environ, {'ASSESSMENT_PATIENT_PASSWORD': ''}), patch('getpass.getpass', side_effect=AssertionError('prompt')):
            with self.assertRaisesMessage(CommandError, 'Missing required'): self.run_seed()
        self.assertFalse(User.objects.exists())

    def test_wrong_targets_and_environment(self):
        for key, value in [('ASSESSMENT_EXPECTED_DB_NAME', 'wrong'),
                           ('ASSESSMENT_EXPECTED_DB_HOST', 'wrong'),
                           ('ASSESSMENT_EXPECTED_SERVICE_ID', 'wrong'),
                           ('RENDER', 'false'), ('DJANGO_SETTINGS_MODULE', 'config.test_settings'),
                           ('DATABASE_URL', 'postgresql://fixture:secret@dpg-test.oregon-postgres.render.com/wrong')]:
            with self.subTest(key=key), patch.dict(os.environ, {key: value}):
                with self.assertRaises(CommandError): self.run_seed()
        self.assertFalse(User.objects.exists())

    def test_retry_preserves_all_records_and_passwords(self):
        other = User.objects.create_user('unrelated', password='fixture-only-password')
        self.assertIn('RENDER ASSESSMENT DEMO SEED VERIFIED', self.run_seed())
        Patient.objects.create(user=other)
        doctor = Doctor.objects.first()
        day = timezone.localdate() + timedelta(days=35)
        while day.weekday() > 4:
            day += timedelta(days=1)
        book_appointment(other, doctor, available_slots(doctor, day)[0], 'Unrelated existing booking')
        before = list(Appointment.objects.values())
        users = list(User.objects.order_by('pk').values())
        self.run_seed()
        self.assertEqual(before, list(Appointment.objects.values()))
        self.assertEqual(users, list(User.objects.order_by('pk').values()))
        self.assertEqual(Appointment.objects.count(), 101)
        self.assertEqual(Doctor.objects.count(), 5)
        other.refresh_from_db(); self.assertTrue(other.check_password('fixture-only-password'))
        with patch.dict(os.environ, {'ASSESSMENT_PATIENT_PASSWORD': secrets.token_urlsafe(32)}):
            with self.assertRaises(CommandError): self.run_seed()
        self.assertEqual(users, list(User.objects.order_by('pk').values()))
        self.assertEqual(before, list(Appointment.objects.values()))

    def test_verification_failure_rolls_back_and_redacts(self):
        from django.core.management import call_command as real_call
        def fail_verify(name, **kwargs):
            if name == 'verify_assessment_demo':
                raise RuntimeError(self.env['DATABASE_URL'] + self.env['ASSESSMENT_ADMINISTRATOR_PASSWORD'])
            return real_call(name, **kwargs)
        with patch('clinic.management.commands.run_render_demo_seed.call_command', side_effect=fail_verify):
            with self.assertRaisesMessage(CommandError, 'rolled back') as error:
                self.run_seed()
        self.assertNotIn('private-url-secret', str(error.exception))
        self.assertNotIn(self.env['ASSESSMENT_ADMINISTRATOR_PASSWORD'], str(error.exception))
        self.assertFalse(User.objects.exists()); self.assertFalse(Appointment.objects.exists())

    def test_build_order_and_default(self):
        script = Path('scripts/render-build.sh').read_text(encoding='utf-8-sig')
        self.assertLess(script.index('migrate --check'), script.index('run_render_demo_seed'))
        self.assertIn('${RUN_ASSESSMENT_DEMO_SEED:-false}', script)
        self.assertIn('check --deploy --fail-level WARNING', script)
