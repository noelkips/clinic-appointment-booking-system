from unittest.mock import patch

from django.db import OperationalError
from django.test import SimpleTestCase, TestCase, override_settings


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
