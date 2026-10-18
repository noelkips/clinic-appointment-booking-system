import getpass
import os
from datetime import datetime, timedelta, time
from pathlib import Path
from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from clinic.models import Appointment, AppointmentEvent, Doctor, DoctorAvailability, Patient
from clinic.services import validate_slot

DOCTORS = [
    ('Amara','Njoroge','General Medicine','A thoughtful approach to everyday health, preventive care, and helping you plan your next steps.'),
    ('Daniel','Otieno','Pediatrics','Welcoming care for children and their families, with time for questions and practical guidance.'),
    ('Leila','Hassan','Dermatology','A calm, attentive approach to skin concerns and clear, understandable care planning.'),
    ('Samuel','Kiptoo','Cardiology','Focused on heart health conversations, preventive guidance, and making appointments feel less overwhelming.'),
    ('Zuri','Kamau','Orthopedics','Supporting movement and everyday comfort through considered consultations and individual care planning.'),
]
PATIENTS = [('Amina','Wambui'),('Brian','Odhiambo'),('Chloe','Kibet'),('David','Muriithi'),('Esther','Achieng'),('Felix','Barasa'),('Grace','Moraa'),('Hassan','Abdi'),('Ivy','Chebet'),('James','Mutua'),('Karen','Wanjiku'),('Leon','Kimani'),('Maya','Wekesa'),('Noah','Kariuki'),('Olivia','Naliaka'),('Peter','Omondi'),('Quinn','Cherono'),('Ruth','Muthoni'),('Simon','Koech'),('Talia','Nyambura')]

class Command(BaseCommand):
    help = 'Create local fictional demo records. Password comes from DEMO_PASSWORD or a hidden prompt.'
    def add_arguments(self, parser):
        parser.add_argument('--reset-passwords', action='store_true', help='Deliberately reset only marked demo account passwords.')
        parser.add_argument('--no-reference', action='store_true', help='Do not write a local credential reference (useful for tests).')

    def handle(self, *args, **options):
        host = settings.DATABASES['default'].get('HOST', '')
        if not settings.DEBUG or not settings.DEMO_SEED_ENABLED or host not in ('', 'localhost', '127.0.0.1', '::1'):
            raise CommandError('Demo seeding requires DEBUG, DEMO_SEED_ENABLED and a loopback/local database. Production execution is disabled.')
        password = os.environ.get('DEMO_PASSWORD') or getpass.getpass('Local demo password: ')
        if len(password) < 8:
            raise CommandError('Use at least eight characters.')
        rows=[]
        with transaction.atomic():
            group,_=Group.objects.get_or_create(name='__savannah_local_demo__')
            Group.objects.select_for_update().get(pk=group.pk)
            def account(username,first,last,staff=False):
                email=username+'@demo.example.test'
                existing=User.objects.filter(username=username).first()
                if existing and (existing.email!=email or not existing.groups.filter(pk=group.pk).exists()):
                    raise CommandError('Refusing to overwrite an unmarked existing account: '+username)
                user,created=User.objects.get_or_create(username=username,defaults={'email':email,'first_name':first,'last_name':last,'is_staff':staff,'is_superuser':staff})
                if not user.is_active or user.is_staff != staff or user.is_superuser != staff:
                    raise CommandError('Existing demo account role/active state has changed: '+username)
                if created or options['reset_passwords']:
                    user.set_password(password);user.save();user.groups.add(group)
                if authenticate(username=username,password=password) is None:
                    raise CommandError('Demo password differs. Use --reset-passwords deliberately for marked accounts.')
                rows.append(('Administrator' if staff else ('Doctor' if username.startswith('doctor') else 'Patient'),username,user.get_full_name()))
                return user
            account('admin','Nia','Mbeki',True)
            account('admin2','Elias','Wambua',True)
            doctors=[]
            for index,(first,last,specialty,bio) in enumerate(DOCTORS,1):
                user=account('doctor'+str(index),first,last)
                doctor,_=Doctor.objects.get_or_create(user=user,defaults={'specialty':specialty,'biography':bio})
                doctors.append(doctor)
                for weekday in range(7):
                    periods=[(time(9),time(12)),(time(14),time(17))] if index<=2 else [(time(9),time(17))]
                    for begin,end in periods:
                        row,created=DoctorAvailability.objects.get_or_create(doctor=doctor,weekday=weekday,start_time=begin,defaults={'end_time':end,'slot_minutes':30})
                        row.full_clean()
            patients=[]
            for index,(first,last) in enumerate(PATIENTS,1):
                user=account('patient'+str(index),first,last)
                patient,_=Patient.objects.get_or_create(user=user)
                patients.append(patient)
            today=timezone.localdate()
            for index in range(100):
                doctor=doctors[index%5]
                patient=patients[index%20]
                reason='Demo consultation '+str(index+1).zfill(3)
                if Appointment.objects.filter(patient=patient,reason=reason).exists():
                    continue
                day=today+timedelta(days=index//5-8)
                start=timezone.make_aware(datetime.combine(day,time(9+(index%3),30 if index%2 else 0)))
                historical=start<timezone.now()
                validate_slot(doctor,start,patient.pk,historical=historical)
                obj=Appointment.objects.create(patient=patient,doctor=doctor,starts_at=start,reason=reason,status='cancelled' if index%7==0 else 'confirmed')
                booked_at=start-timedelta(days=2+index%6)
                if booked_at>timezone.now():
                    booked_at=timezone.now()-timedelta(hours=1+index%48)
                Appointment.objects.filter(pk=obj.pk).update(created_at=booked_at)
                AppointmentEvent.objects.create(appointment=obj,actor=patient.user,action='booked',occurred_at=booked_at)
                if obj.status=='cancelled':
                    AppointmentEvent.objects.create(appointment=obj,actor=patient.user,action='cancelled',occurred_at=booked_at+timedelta(minutes=10))
        if not options['no_reference']:
            output=Path(settings.BASE_DIR)/'docs/LOCAL_TEST_ACCOUNTS.md'
            text='# Local demonstration accounts\n\nFictional development data only. Do not commit or deploy this file.\n\n| Role | Username | Name | Password |\n|---|---|---|---|\n'
            for role_name,username,name in rows:
                text+='| '+role_name+' | '+username+' | '+name+' | '+password+' |\n'
            output.write_text(text,encoding='utf-8')
        self.stdout.write(self.style.SUCCESS('Verified 27 active demo accounts. Dataset: '+str(Appointment.objects.filter(reason__startswith='Demo consultation ').count())+' demo appointments.'))
