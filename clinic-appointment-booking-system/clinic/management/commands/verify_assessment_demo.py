"""Read-only fixture and authentication verification; creates no login sessions."""
import getpass
import json
import os
from datetime import timedelta

from django.contrib.auth import authenticate
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from clinic.management.commands.seed_assessment_demo import GROUP, PRIMARY
from clinic.models import Appointment, AppointmentEvent, Doctor, Patient
from clinic.services import available_slots, role


class Command(BaseCommand):
    help = 'Read-only totals, fixture coverage, future slots and three password/role checks.'

    def add_arguments(self, parser):
        parser.add_argument('--no-input', action='store_true', help='Read passwords from environment; never prompt.')

    def handle(self, *args, **options):
        if options['no_input'] and any(not os.getenv('ASSESSMENT_' + kind.upper() + '_PASSWORD') for kind in PRIMARY):
            raise CommandError('Missing required assessment password environment variables.')
        doctors = Doctor.objects.filter(user__groups__name=GROUP)
        patients = Patient.objects.filter(user__groups__name=GROUP)
        visits = Appointment.objects.filter(doctor__in=doctors, patient__in=patients,
                                           reason__startswith='Assessment demo v1 visit ')
        now = timezone.now()
        report = {
            'totals': {'doctors': Doctor.objects.count(), 'patients': Patient.objects.count(),
                       'appointments': Appointment.objects.count()},
            'fixtures': {'doctors': doctors.count(), 'patients': patients.count(),
                         'appointments': visits.count(),
                         'confirmed': visits.filter(status='confirmed').count(),
                         'cancelled': visits.filter(status='cancelled').count(),
                         'historical': visits.filter(starts_at__lt=now).count(),
                         'future_confirmed': visits.filter(starts_at__gt=now, status='confirmed').count(),
                         'rescheduled_events': AppointmentEvent.objects.filter(appointment__in=visits, action='rescheduled').count()},
            'future_slots_next_14_days': {}, 'logins': {},
        }
        for doctor in doctors.select_related('user'):
            slots = [slot for i in range(1, 15) for slot in available_slots(
                doctor, timezone.localdate()+timedelta(days=i))]
            report['future_slots_next_14_days'][doctor.user.username] = {
                'count': len(slots), 'first': slots[0].isoformat() if slots else None}
        for expected, username in PRIMARY.items():
            password = (os.environ['ASSESSMENT_' + expected.upper() + '_PASSWORD'] if options['no_input']
                        else getpass.getpass(f'{username} password (hidden): '))
            user = authenticate(username=username, password=password)
            owned = user is not None and user.groups.filter(name=GROUP).exists()
            report['logins'][username] = bool(owned and role(user) == expected and not user.is_superuser)
        self.stdout.write(json.dumps(report, indent=2))
        fixture = report['fixtures']
        if (fixture['doctors'] != 5 or fixture['patients'] != 20 or fixture['appointments'] != 100
                or any(not fixture[key] for key in ('confirmed', 'cancelled', 'historical', 'future_confirmed', 'rescheduled_events'))
                or not all(report['logins'].values())
                or not all(row['count'] for row in report['future_slots_next_14_days'].values())):
            raise CommandError('Verification failed; review the credential-free report. No data changed.')
