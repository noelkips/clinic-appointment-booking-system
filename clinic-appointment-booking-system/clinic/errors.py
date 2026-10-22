"""Safe shared error responses. Never serialize exception text for server errors."""
from django.http import JsonResponse
from django.db import DatabaseError
from rest_framework.authentication import SessionAuthentication

ERRORS = {
    400: ('invalid_request', 'Check the information you entered and try again.'),
    401: ('authentication_required', 'Your session may have expired. Sign in and try again.'),
    403: ('permission_denied', 'You do not have permission to do this. Appointment booking requires a patient account.'),
    404: ('not_found', 'We could not find that page or appointment. Check the address or return home.'),
    405: ('method_not_allowed', 'This operation is not supported. Use the available page controls.'),
    409: ('appointment_conflict', 'That time is no longer available. Choose another available slot.'),
    429: ('too_many_requests', 'Too many requests. Please wait before trying again.'),
    500: ('server_error', 'Something went wrong. Please try again later.'),
    503: ('service_unavailable', 'The service is temporarily unavailable. Please wait a moment and try again.'),
}


def is_api(request):
    match = getattr(request, 'resolver_match', None)
    return request.path.startswith('/api/') or bool(match and getattr(match.func, 'cls', None))


def payload(status, details=None, message=None, code=None):
    default_code, default_message = ERRORS.get(status, ERRORS[500])
    return {'error': {'code': code or default_code, 'message': message or default_message,
                      'details': details or {}}}


def error_response(request, status, message=None, code=None):
    data = payload(status, message=message, code=code)
    if is_api(request):
        response = JsonResponse(data, status=status)
    else:
        # Standalone template deliberately avoids user/profile/database context processors.
        from django.template.loader import get_template
        from django.http import HttpResponse
        response = HttpResponse(get_template('errors/error.html').render({
            'status': status, **data['error']}), status=status)
    response['Cache-Control'] = 'no-store'
    return response


def bad_request(request, exception=None): return error_response(request, 400)
def forbidden(request, exception=None): return error_response(request, 403)
def not_found(request, exception=None): return error_response(request, 404)
def server_error(request): return error_response(request, 500)
def csrf_failure(request, reason=''):
    return error_response(request, 403, 'Your security token has expired or is missing. Reload the form, sign in if needed, and submit again.', 'csrf_failed')


class SessionAuthenticationWithChallenge(SessionAuthentication):
    def authenticate_header(self, request):
        return 'Session'


def api_exception_handler(exc, context):
    from rest_framework.views import exception_handler
    response = exception_handler(exc, context)
    if response is None:
        import logging
        logging.getLogger(__name__).error('API request failed', exc_info=(type(exc), exc, exc.__traceback__))
        return error_response(context['request'], 503 if isinstance(exc, DatabaseError) else 500)
    # CSRF failure text comes from DRF; replace its diagnostic reason.
    if response.status_code == 403 and isinstance(response.data, dict) and str(response.data.get('detail', '')).startswith('CSRF Failed'):
        response.data = payload(403, code='csrf_failed', message='Your security token has expired or is missing. Reload the form and try again.')
    return response


class ErrorResponseMiddleware:
    def __init__(self, get_response): self.get_response = get_response

    def process_view(self, request, view_func, view_args, view_kwargs):
        if getattr(view_func, '__module__', '') != 'clinic.views': return None
        mutable = {'book', 'appointment_detail', 'platform_doctor', 'platform_schedules'}
        allowed = ('GET', 'HEAD', 'POST') if view_func.__name__ in mutable else ('GET', 'HEAD')
        if request.method not in allowed and not hasattr(view_func, 'view_class'):
            response = error_response(request, 405)
            response['Allow'] = ', '.join(allowed)
            return response

    def process_exception(self, request, exception):
        from django.core.exceptions import PermissionDenied, SuspiciousOperation
        from django.http import Http404
        if isinstance(exception, (Http404, PermissionDenied, SuspiciousOperation)):
            return None
        import logging
        logging.getLogger(__name__).error('Web request failed', exc_info=(type(exception), exception, exception.__traceback__))
        return error_response(request, 503 if isinstance(exception, DatabaseError) else 500)

    def __call__(self, request):
        response = self.get_response(request)
        if response.status_code not in ERRORS:
            return response
        if is_api(request):
            import json
            try:
                data = response.data if hasattr(response, 'data') else json.loads(response.content)
            except (ValueError, AttributeError):
                data = {}
            if isinstance(data, dict) and 'error' in data:
                body = data
            else:
                # Keep validation details only for expected client errors.
                details = data if response.status_code < 500 else {}
                body = payload(response.status_code, details)
            if hasattr(response, 'data'):
                response.data = body
            response.content = json.dumps(body)
            response['Content-Type'] = 'application/json'
            response['Content-Length'] = str(len(response.content))
        elif response.status_code in (405, 429, 503):
            replacement = error_response(request, response.status_code)
            for header in ('Allow', 'Retry-After'):
                if header in response: replacement[header] = response[header]
            return replacement
        response['Cache-Control'] = 'no-store'
        return response
