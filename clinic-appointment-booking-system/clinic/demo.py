"""Local demo ownership checks; shared by seeding and explicit credential rotation."""
from pathlib import Path
from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.core.management.base import CommandError
from django.db import transaction

DEMO_GROUP = '__savannah_local_demo__'
DEMO_USERNAMES = ['admin', 'admin2'] + [f'doctor{i}' for i in range(1, 6)] + [f'patient{i}' for i in range(1, 21)]


def require_local_demo():
    host = settings.DATABASES['default'].get('HOST', '')
    if not settings.DEBUG or not settings.DEMO_SEED_ENABLED or host not in ('', 'localhost', '127.0.0.1', '::1'):
        raise CommandError('Demo operations require DEBUG, DEMO_SEED_ENABLED and a loopback/local database. Production execution is disabled.')


def write_reference(users, password):
    text = '# Savannah Clinic local demonstration accounts\n\nLocal development only. Never commit or deploy this file.\n\n| Role | Username | Name | Password |\n|---|---|---|---|\n'
    for user in users:
        kind = 'Administrator' if user.is_staff else ('Doctor' if hasattr(user, 'doctor_profile') else 'Patient')
        text += f'| {kind} | {user.username} | {user.get_full_name()} | {password} |\n'
    output = Path(settings.BASE_DIR) / 'docs/LOCAL_TEST_ACCOUNTS.md'
    output.write_text(text, encoding='utf-8')


@transaction.atomic
def rotate_passwords(password, previous_password=None):
    require_local_demo()
    if len(password) < 8:
        raise CommandError('Use at least eight characters.')
    users = list(User.objects.select_for_update().filter(username__in=DEMO_USERNAMES))
    if {user.username for user in users} != set(DEMO_USERNAMES):
        raise CommandError('All 27 designated demo users must already exist. No accounts were changed.')
    # Validate the entire set before changing any password, including admin.
    for user in users:
        staff = user.username in ('admin', 'admin2')
        if (not user.groups.filter(name=DEMO_GROUP).exists()
                or user.email != user.username + '@demo.example.test'
                or not user.is_active or user.is_staff != staff or user.is_superuser != staff
                or (user.username.startswith('doctor') and not hasattr(user, 'doctor_profile'))
                or (user.username.startswith('patient') and not hasattr(user, 'patient_profile'))):
            raise CommandError(f'Cannot confidently identify {user.username} as its designated demo role. No accounts were changed.')
    for user in users:
        user.set_password(password)
        user.save(update_fields=['password'])
    for user in users:
        if authenticate(username=user.username, password=password) is None:
            raise CommandError(f'New demo credential verification failed for {user.username}. Changes rolled back.')
        if previous_password is not None and authenticate(username=user.username, password=previous_password) is not None:
            raise CommandError(f'Previous credential still authenticates {user.username}. Changes rolled back.')
    order = {name: index for index, name in enumerate(DEMO_USERNAMES)}
    return sorted(users, key=lambda user: order[user.username])


def validate_demo_slot(doctor, starts, patient_id):
    """Only explicitly enabled local demo generation may insert valid past slots."""
    from django.utils import timezone
    from .services import validate_slot
    require_local_demo()
    validate_slot(doctor, starts, patient_id, historical=starts < timezone.now())
