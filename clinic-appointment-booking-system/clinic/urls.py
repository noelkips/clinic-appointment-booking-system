from django.urls import include, path
from . import views
urlpatterns = [
    path('', views.home, name='home'),
    path('doctors/', views.doctors, name='doctors'),
    path('doctors/<int:pk>/', views.doctor_detail, name='doctor-detail'),
    path('dashboard/', views.patient_dashboard, name='patient-dashboard'),
    path('dashboard/redirect/', views.dashboard, name='dashboard'),
    path('doctor-dashboard/', views.doctor_dashboard, name='doctor-dashboard'),
    path('doctor-dashboard/schedule/', views.doctor_schedule, name='doctor-schedule'),
    path('appointments/', views.appointments, name='appointment-list'),
    path('appointments/book/', views.book, name='book'),
    path('appointments/<int:pk>/', views.appointment_detail, name='appointment-detail'),
    path('account/', views.account, name='account'),
    path('platform/', views.platform, name='platform'),
    path('platform/appointments/', views.platform_appointments, name='platform-appointments'),
    path('platform/doctors/', views.platform_doctors, name='platform-doctors'),
    path('platform/doctors/<int:pk>/', views.platform_doctor, name='platform-doctor'),
    path('platform/patients/', views.platform_patients, name='platform-patients'),
    path('platform/patients/<int:pk>/', views.platform_patient, name='platform-patient'),
    path('platform/schedules/', views.platform_schedules, name='platform-schedules'),
    path('platform/activity/', views.platform_activity, name='platform-activity'),
    path('', include('clinic.api_urls')),
]
