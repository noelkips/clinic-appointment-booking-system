from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.shortcuts import redirect, render
from django.views import View
from .forms import AppointmentForm, RegisterForm
from .models import Appointment, Doctor

@login_required
def dashboard(request):
    appointments = Appointment.objects.select_related('patient__user','doctor__user').filter(status=Appointment.Status.CONFIRMED)
    context = {'appointments': appointments[:8], 'appointment_count': appointments.count(), 'doctor_count': Doctor.objects.filter(is_available=True).count(), 'patient_count': appointments.values('patient').distinct().count(), 'appointment_form': AppointmentForm()}
    return render(request, 'dashboard/index.html', context)

@login_required
def book(request):
    if not hasattr(request.user, 'patient_profile'): return redirect('dashboard')
    form = AppointmentForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        appointment = form.save(commit=False); appointment.patient = request.user.patient_profile; appointment.starts_at = form.cleaned_data['starts_at']
        try: appointment.full_clean(); appointment.save()
        except Exception: form.add_error(None, 'That appointment slot is no longer available.')
        else: messages.success(request, 'Appointment confirmed and saved.'); return redirect('dashboard')
    return render(request, 'appointments/booking.html', {'form': form})

class RegisterView(View):
    def get(self, request): return render(request, 'accounts/register.html', {'form': RegisterForm()})
    def post(self, request):
        form = RegisterForm(request.POST)
        if form.is_valid(): login(request, form.save()); return redirect('dashboard')
        return render(request, 'accounts/register.html', {'form': form})
