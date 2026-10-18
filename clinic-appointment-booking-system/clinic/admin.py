from django.contrib import admin
from .models import Appointment, Doctor, DoctorAvailability, Patient
admin.site.register([Doctor, DoctorAvailability, Patient, Appointment])
