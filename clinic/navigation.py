"""Named, role-aware navigation shared by every server-rendered page."""
from django.urls import reverse
from .services import role


MENUS = {
    'administrator': [
        ('Overview', 'platform', 'overview', ['platform']),
        ('Appointments', 'platform-appointments', 'calendar', ['platform-appointments', 'appointment-detail']),
        ('Doctors', 'platform-doctors', 'doctor', ['platform-doctors', 'platform-doctor']),
        ('Patients', 'platform-patients', 'people', ['platform-patients', 'platform-patient']),
        ('Working schedules', 'platform-schedules', 'clock', ['platform-schedules']),
        ('Activity', 'platform-activity', 'activity', ['platform-activity']),
    ],
    'doctor': [
        ('Dashboard', 'doctor-dashboard', 'overview', ['doctor-dashboard']),
        ('My appointments', 'appointment-list', 'calendar', ['appointment-list', 'appointment-detail']),
        ('My schedule', 'doctor-schedule', 'clock', ['doctor-schedule']),
    ],
    'patient': [
        ('Dashboard', 'patient-dashboard', 'overview', ['patient-dashboard']),
        ('Find doctors', 'doctors', 'doctor', ['doctors', 'doctor-detail']),
        ('Book appointment', 'book', 'calendar', ['book']),
        ('My appointments', 'appointment-list', 'clock', ['appointment-list', 'appointment-detail']),
    ],
}


def navigation_context(request):
    current_role = role(request.user)
    route = request.resolver_match.url_name if request.resolver_match else ''
    definitions = MENUS.get(current_role, []) + [('Account', 'account', 'account', ['account'])]
    items = [dict(label=label, url=reverse(name), icon=icon, active=route in active_names)
             for label, name, icon, active_names in definitions]
    title = {
        'platform': 'Overview', 'platform-appointments': 'Appointments',
        'platform-doctors': 'Doctors', 'platform-doctor': 'Doctor profile',
        'platform-patients': 'Patients', 'platform-patient': 'Patient profile',
        'platform-schedules': 'Working schedules', 'platform-activity': 'Activity',
        'patient-dashboard': 'Dashboard', 'doctor-dashboard': 'Dashboard',
        'doctor-schedule': 'My schedule', 'appointment-list': 'My appointments',
        'appointment-detail': 'Appointment details', 'book': 'Book appointment',
        'account': 'My account',
    }.get(route, 'Workspace')
    parent = next((item for item in items if item['active'] and item['url'] != request.path), None)
    return {
        'current_role': current_role, 'navigation_items': items,
        'navigation_title': title, 'navigation_parent': parent,
        'workspace_url': reverse({'administrator': 'platform', 'doctor': 'doctor-dashboard'}.get(current_role, 'patient-dashboard')),
        'public_home_active': route == 'home',
        'public_doctors_active': route in ('doctors', 'doctor-detail'),
    }
