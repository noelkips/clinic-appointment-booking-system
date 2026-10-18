from django.urls import path
from . import api
urlpatterns = [path('appointments', api.create_appointment), path('doctors/<int:pk>/availability', api.availability), path('appointments/<int:pk>/cancel', api.cancel_appointment), path('appointments/<int:pk>/reschedule', api.reschedule_appointment), path('patients/<int:pk>/appointments', api.patient_appointments)]
