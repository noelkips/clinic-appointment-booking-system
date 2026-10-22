from unittest.mock import patch
from django.test import Client, SimpleTestCase, TestCase, override_settings
from django.db import OperationalError
from . import tests as fixtures
from .errors import error_response
from django.test import RequestFactory


class ReliabilityTests(TestCase):
    setUpTestData = classmethod(fixtures.ClinicTests.setUpTestData.__func__)
    api = fixtures.ClinicTests.api
    post = fixtures.ClinicTests.post
    create = fixtures.ClinicTests.create
    def test_booking_role_matrix(self):
        for user, status in [(self.admin, 403), (self.doctor_user, 403), (self.patient_user, 201)]:
            with self.subTest(user=user.username):
                self.client.force_login(user)
                response = self.client.get('/appointments/book/')
                self.assertEqual(response.status_code, 200 if status == 201 else status)
                response = self.post(user=user)
                self.assertEqual(response.status_code, status)
                if status == 403:
                    self.assertEqual(response.json()['error']['code'], 'permission_denied')

    def test_public_booking_actions_follow_role(self):
        for user in (self.admin, self.doctor_user):
            self.client.force_login(user)
            for url in ('/', f'/doctors/{self.doctor.pk}/'):
                response = self.client.get(url)
                self.assertNotContains(response, 'href="/appointments/book/')
                self.assertContains(response, 'Booking is available to patient accounts only.')

    def test_api_anonymous_and_expired_sessions(self):
        for prefix in ('/api', ''):
            response = self.api().post(prefix + '/appointments', {}, format='json')
            self.assertEqual(response.status_code, 401)
            self.assertEqual(response.json()['error']['code'], 'authentication_required')
            self.assertEqual(response['WWW-Authenticate'], 'Session')
        self.client.cookies['sessionid'] = 'expired-session'
        self.assertEqual(self.client.get('/appointments/book/').status_code, 302)

    def test_api_validation_and_conflicts(self):
        response = self.api(self.patient_user).post('/api/appointments', {}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('doctor', response.json()['error']['details'])
        self.assertEqual(int(response['Content-Length']), len(response.content))
        response = self.api(self.patient_user).post('/api/appointments', {}, format='json', HTTP_ACCEPT='text/html')
        self.assertEqual(response['Content-Type'], 'application/json')
        self.assertIn('doctor', response.json()['error']['details'])
        self.create()
        response = self.post(user=self.other_user)
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()['error']['code'], 'appointment_conflict')

    def test_html_bound_form_and_conflict_status(self):
        self.client.force_login(self.patient_user)
        response = self.client.post('/appointments/book/', {'reason': 'Keep my reason'})
        self.assertContains(response, 'Keep my reason', status_code=400)
        self.create()
        self.client.force_login(self.other_user)
        response = self.client.post('/appointments/book/', {'doctor': self.doctor.pk,
            'date': self.day.isoformat(), 'starts_at': self.start.isoformat(), 'reason': 'Keep this too'})
        self.assertContains(response, 'Keep this too', status_code=409)
        self.assertContains(response, self.start.isoformat(), status_code=409)

    def test_csrf_protected_html_and_api(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.patient_user)
        for url in ('/appointments/book/', '/api/appointments'):
            response = client.post(url, {})
            self.assertEqual(response.status_code, 403)
            self.assertNotContains(response, 'CSRF cookie not set', status_code=403)
            if url.startswith('/api'):
                self.assertEqual(response.json()['error']['code'], 'csrf_failed')
        page = client.get('/appointments/book/')
        token = client.cookies['csrftoken'].value
        response = client.post('/api/appointments', {'doctor': self.doctor.pk,
            'starts_at': self.start.isoformat()}, HTTP_X_CSRFTOKEN=token)
        self.assertEqual(response.status_code, 201)

    def test_throttle_headers_and_parse_errors(self):
        from rest_framework.exceptions import Throttled
        with patch('clinic.api.book_appointment', side_effect=Throttled(wait=10)):
            response = self.post()
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response['Retry-After'], '10')
        self.assertEqual(response.json()['error']['code'], 'too_many_requests')
        client = self.api(self.patient_user)
        response = client.post('/api/appointments', '{invalid', content_type='application/json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error']['code'], 'invalid_request')

    def test_cancelled_appointment_error_remains_visible(self):
        obj = self.create()
        from .services import change_appointment
        change_appointment(self.patient_user, obj.pk, 'cancelled', cancellation_reason='Cannot attend')
        self.client.force_login(self.patient_user)
        response = self.client.post(f'/appointments/{obj.pk}/', {'action': 'cancelled', 'reason': 'Again'})
        self.assertContains(response, 'Only upcoming confirmed appointments can be changed.', status_code=400)

    def test_web_unexpected_and_database_errors_are_safe(self):
        for exc, status in ((RuntimeError('private-web'), 500), (OperationalError('private-db'), 503)):
            with patch('clinic.views.available_slots', side_effect=exc):
                response = self.client.get(f'/doctors/{self.doctor.pk}/')
            self.assertEqual(response.status_code, status)
            self.assertNotContains(response, 'private-', status_code=status)

    @override_settings(DEBUG=False)
    def test_safe_errors_and_methods(self):
        for url in ('/missing-page/', '/api/missing-page/'):
            response = self.client.get(url)
            self.assertEqual(response.status_code, 404)
            self.assertNotContains(response, 'Traceback', status_code=404)
        self.client.force_login(self.patient_user)
        response = self.client.put('/appointments/book/')
        self.assertEqual(response.status_code, 405)
        self.assertIn('POST', response['Allow'])
        response = self.api(self.patient_user).get('/api/appointments')
        self.assertEqual(response.status_code, 405)
        self.assertEqual(response.json()['error']['code'], 'method_not_allowed')
        for exc, status in ((RuntimeError('private-secret'), 500), (OperationalError('private-host'), 503)):
            with patch('clinic.api.book_appointment', side_effect=exc):
                response = self.post()
            self.assertEqual(response.status_code, status)
            self.assertNotContains(response, 'private-', status_code=status)


class ErrorPagesTests(SimpleTestCase):
    def test_all_error_templates_are_safe(self):
        for status in (400, 401, 403, 404, 405, 409, 429, 500, 503):
            for path in ('/page/', '/api/page/'):
                response = error_response(RequestFactory().get(path), status)
                self.assertEqual(response.status_code, status)
                self.assertEqual(response['Cache-Control'], 'no-store')
                self.assertNotIn(b'Traceback', response.content)

    def test_health_without_database(self):
        response = self.client.get('/health/')
        self.assertEqual(response.json(), {'status': 'ok'})
        self.assertEqual(self.client.head('/health/').status_code, 200)
        self.assertEqual(self.client.post('/health/').status_code, 405)
