from unittest.mock import patch
import base64
import os
import runpy
import secrets
from pathlib import Path

from django.core.checks.security.base import check_secret_key
from django.core.exceptions import ImproperlyConfigured
from django.db import OperationalError
from django.test import SimpleTestCase, TestCase, override_settings


class SecretConfigurationTests(SimpleTestCase):
    def test_render_generated_value_triggers_django_length_warning(self):
        key = base64.b64encode(secrets.token_bytes(32)).decode('ascii')
        self.assertEqual(len(key), 44)
        with override_settings(SECRET_KEY=key):
            self.assertEqual([warning.id for warning in check_secret_key(None)], ['security.W009'])

    def test_long_random_secret_passes(self):
        with override_settings(SECRET_KEY=secrets.token_urlsafe(64)):
            self.assertEqual(check_secret_key(None), [])

    def test_environment_secret_takes_precedence_over_dotenv(self):
        key = secrets.token_urlsafe(64)
        with patch.dict(os.environ, {'DJANGO_SECRET_KEY': key, 'DJANGO_DEBUG': 'True'}):
            # Use the actual loader and local file, with explicit non-override semantics.
            namespace = runpy.run_path(str(Path(__file__).with_name('settings.py')))
            self.assertTrue(namespace['SECRET_KEY'] == key)

    def test_missing_secret_has_no_development_fallback(self):
        with patch.dict(os.environ, {'DJANGO_SECRET_KEY': ''}), patch('dotenv.load_dotenv'):
            with self.assertRaisesMessage(ImproperlyConfigured, 'Set DJANGO_SECRET_KEY.'):
                runpy.run_path(str(Path(__file__).with_name('settings.py')))


class HealthTests(TestCase):
    def test_database_health(self):
        response = self.client.get('/health/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'status': 'ok'})
        self.assertEqual(response['Cache-Control'], 'no-store')

    def test_database_failure_is_generic(self):
        with patch('config.health.connection.cursor', side_effect=OperationalError('private connection detail')):
            response = self.client.get('/health/')
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {'status': 'unavailable'})
        self.assertNotContains(response, 'private', status_code=503)

    def test_health_rejects_mutation(self):
        self.assertEqual(self.client.post('/health/').status_code, 405)


@override_settings(SECURE_SSL_REDIRECT=True,
                   SECURE_PROXY_SSL_HEADER=('HTTP_X_FORWARDED_PROTO', 'https'))
class ProxyTests(SimpleTestCase):
    def test_http_redirects_to_https(self):
        response = self.client.get('/accounts/login/')
        self.assertEqual(response.status_code, 301)
        self.assertEqual(response['Location'], 'https://testserver/accounts/login/')

    def test_trusted_https_does_not_loop(self):
        response = self.client.get('/accounts/login/', HTTP_X_FORWARDED_PROTO='https')
        self.assertEqual(response.status_code, 200)
