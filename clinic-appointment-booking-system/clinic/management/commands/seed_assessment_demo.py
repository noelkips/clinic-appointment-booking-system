"""Explicit, additive hosted assessment fixtures; never called by a build."""
import getpass
import os
from datetime import datetime, time, timedelta

from django.conf import settings
from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.utils import timezone

from clinic.management.commands.seed_demo import DOCTORS, PATIENTS
from clinic.models import Appointment, AppointmentEvent, Doctor, DoctorAvailability, Patient
from clinic.services import change_appointment, validate_slot

GROUP = '__savannah_assessment_demo_v1__'
PRIMARY = {'administrator': 'demo_admin', 'doctor': 'demo_doctor', 'patient': 'demo_patient'}


def roster():
    return ([('demo_admin', 'Assessment', 'Administrator', 'administrator'),
             ('assessment_admin2', 'Assessment', 'Support', 'administrator')]
            + [(('demo_doctor' if i == 0 else f'assessment_doctor{i+1}'), row[0], row[1], 'doctor') for i, row in enumerate(DOCTORS)]
            + [(('demo_patient' if i == 0 else f'assessment_patient{i+1}'), row[0], row[1], 'patient') for i, row in enumerate(PATIENTS)])


class Command(BaseCommand):
    help = 'Inspect or explicitly create isolated assessment fixtures. Never resets/deletes data.'

    def add_arguments(self, parser):
        parser.add_argument('--inspect', action='store_true', help='Read-only counts and intended-name collision report.')
        parser.add_argument('--confirm-database', help='Must exactly match the configured database NAME.')
        parser.add_argument('--rotate-passwords', action='store_true', help='Explicitly change ONLY the three owned reviewer passwords.')

    def handle(self, *args, **options):
        if connection.vendor != 'postgresql':
            raise CommandError('Assessment seeding requires PostgreSQL.')
        if options['inspect']:
            self.stdout.write(str({m.__name__: m.objects.count() for m in (User, Doctor, Patient, DoctorAvailability, Appointment, AppointmentEvent)}))
            self.stdout.write('Intended usernames already present: ' + str(User.objects.filter(username__in=[r[0] for r in roster()]).count()))
            self.stdout.write('Database name for explicit confirmation: ' + str(connection.settings_dict['NAME']))
            return
        if os.getenv('ASSESSMENT_DEMO_ENABLED') != 'True' or options['confirm_database'] != connection.settings_dict['NAME']:
            raise CommandError('Require ASSESSMENT_DEMO_ENABLED=True and exact --confirm-database. Inspect first.')
        passwords = {kind: os.getenv('ASSESSMENT_' + kind.upper() + '_PASSWORD') or getpass.getpass(f'{kind} assessment password: ') for kind in PRIMARY}
        if len(set(passwords.values())) != 3 or any(len(v) < 24 or len(set(v)) < 5 for v in passwords.values()):
            raise CommandError('Use three distinct randomly generated passwords, each at least 24 characters with five distinct characters.')
        # One transaction includes collision checks, users, appointments and events.
        with transaction.atomic():
            group, _ = Group.objects.get_or_create(name=GROUP)
            Group.objects.select_for_update().get(pk=group.pk)
            if group.permissions.exists():
                raise CommandError('Assessment ownership group has unexpected permissions.')
            users = {}
            for username, first, last, kind in roster():
                user = User.objects.filter(username=username).first()
                if user and (not user.groups.filter(pk=group.pk).exists() or user.email != username+'@assessment.example.test'
                             or user.is_staff != (kind == 'administrator') or user.is_superuser or not user.is_active
                             or hasattr(user, 'doctor_profile') != (kind == 'doctor')
                             or hasattr(user, 'patient_profile') != (kind == 'patient')
                             or user.user_permissions.exists() or user.groups.exclude(pk=group.pk).exists()):
                    raise CommandError('Ambiguous or changed assessment identity; refusing all writes: '+username)
                created = user is None
                if created and options['rotate_passwords']:
                    raise CommandError('Rotation requires every assessment identity to exist; no accounts created.')
                if user and username == PRIMARY[kind] and not options['rotate_passwords'] and not user.check_password(passwords[kind]):
                    raise CommandError('Existing reviewer credential differs; use explicit rotation only if authorized.')
                if created:
                    user = User(username=username, first_name=first, last_name=last, email=username+'@assessment.example.test', is_staff=kind=='administrator', is_superuser=False)
                    user.set_unusable_password()
                if username == PRIMARY[kind] and (created or options['rotate_passwords']):
                    user.set_password(passwords[kind])
                if created:
                    user.save()
                    user.groups.add(group)
                    if kind == 'doctor':
                        index = [r[0] for r in roster() if r[3]=='doctor'].index(username)
                        Doctor.objects.create(user=user, specialty=DOCTORS[index][2], biography=DOCTORS[index][3])
                    elif kind == 'patient':
                        Patient.objects.create(user=user)
                elif options['rotate_passwords'] and username == PRIMARY[kind]:
                    user.save(update_fields=['password'])
                users[username] = user
            # Rotation intentionally does not create/repair appointments or schedules.
            if not options['rotate_passwords']:
                doctors = [users[r[0]].doctor_profile for r in roster() if r[3]=='doctor']
                patients = [users[r[0]].patient_profile for r in roster() if r[3]=='patient']
                for doctor in doctors:
                    for weekday in range(5):
                        for begin, end in ((time(9), time(12)), (time(14), time(17))):
                            period, _ = DoctorAvailability.objects.get_or_create(doctor=doctor, weekday=weekday, start_time=begin, defaults={'end_time':end})
                            if period.end_time != end:
                                raise CommandError('Existing assessment schedule changed; review manually.')
                            period.full_clean()
                today = timezone.localdate()
                past = [today-timedelta(days=i) for i in range(1, 22) if (today-timedelta(days=i)).weekday()<5][:10]
                future = [today+timedelta(days=i) for i in range(2, 30) if (today+timedelta(days=i)).weekday()<5][:10]
                days = sorted(past)+future
                for i in range(100):
                    doctor, patient = doctors[i%5], patients[i%20]
                    marker = f'Assessment demo v1 visit {i+1:03}'
                    existing = Appointment.objects.filter(patient=patient, reason=marker)
                    if existing.exists():
                        if existing.count() != 1 or existing.get().doctor_id != doctor.pk:
                            raise CommandError('Ambiguous assessment visit; review manually.')
                        continue
                    start = timezone.make_aware(datetime.combine(days[i//5], time(9+(i//20)%3)))
                    Doctor.objects.select_for_update().get(pk=doctor.pk)
                    Patient.objects.select_for_update().get(pk=patient.pk)
                    validate_slot(doctor, start, patient.pk, historical=start < timezone.now())
                    cancelled = i%7 == 0
                    obj = Appointment.objects.create(doctor=doctor, patient=patient, starts_at=start, reason=marker,
                        status='cancelled' if cancelled else 'confirmed', cancellation_reason='Fictional assessment cancellation' if cancelled else '')
                    booked_at = min(start-timedelta(days=2), timezone.now()-timedelta(hours=2))
                    Appointment.objects.filter(pk=obj.pk).update(created_at=booked_at)
                    AppointmentEvent.objects.create(appointment=obj, actor=patient.user, action='booked', occurred_at=booked_at)
                    if cancelled:
                        AppointmentEvent.objects.create(appointment=obj, actor=patient.user, action='cancelled', occurred_at=booked_at+timedelta(minutes=10))
                    if i == 99:
                        change_appointment(patient.user, obj.pk, 'rescheduled', start+timedelta(minutes=30))
        self.stdout.write(self.style.SUCCESS('Assessment fixtures verified. Owned accounts: 27. Primary logins: demo_admin (staff, not superuser), demo_doctor, demo_patient. No credentials printed.'))
        visits = Appointment.objects.filter(patient__user__groups=group, doctor__user__groups=group,
                                            reason__startswith='Assessment demo v1 visit ')
        self.stdout.write(str({'assessment_visits': visits.count(),
                               'confirmed': visits.filter(status='confirmed').count(),
                               'cancelled': visits.filter(status='cancelled').count()}))
