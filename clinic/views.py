from datetime import date, timedelta
from functools import wraps
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, OperationalError, transaction
from django.db.models import Count, Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views import View
from .forms import CancellationForm, AppointmentForm, DoctorForm, RegisterForm, ScheduleForm, SignInForm
from .models import Appointment, AppointmentEvent, Doctor, DoctorAvailability, Patient
from .services import available_slots, book_appointment, change_appointment, role, visible_appointments


def page(request, template, context=None):
    return render(request, template, {'current_role': role(request.user), 'today': timezone.localdate(), 'now': timezone.now(), **(context or {})})


def admin_required(view):
    @login_required
    @wraps(view)
    def guarded(request, *args, **kwargs):
        if role(request.user) != 'administrator':
            raise PermissionDenied
        return view(request, *args, **kwargs)
    return guarded


def destination(user):
    return {'administrator': 'platform', 'doctor': 'doctor-dashboard'}.get(role(user), 'patient-dashboard')


class SignInView(LoginView):
    authentication_form = SignInForm
    template_name = 'registration/login.html'
    redirect_authenticated_user = True

    def form_valid(self, form):
        response = super().form_valid(form)
        self.request.session.set_expiry(1209600 if form.cleaned_data.get('remember_me') else 0)
        return response

    def get_success_url(self):
        target = self.get_redirect_url()
        allowed = {
            'administrator': ('/platform/', '/django-admin/'),
            'doctor': ('/doctor-dashboard/',),
            'patient': ('/dashboard/', '/appointments/',),
        }.get(role(self.request.user), ())
        if target and any(target.startswith(prefix) for prefix in allowed):
            return target
        return reverse(destination(self.request.user))


class RegisterView(View):
    def get(self, request):
        if request.user.is_authenticated:
            return redirect(destination(request.user))
        return page(request, 'accounts/register.html', {'form': RegisterForm()})

    def post(self, request):
        form = RegisterForm(request.POST)
        if form.is_valid():
            login(request, form.save())
            return redirect('patient-dashboard')
        return page(request, 'accounts/register.html', {'form': form})


def home(request):
    return page(request, 'public/home.html', {'doctors': Doctor.objects.select_related('user').filter(is_available=True, user__is_active=True)[:5]})


def forgot_password(request):
    return page(request, 'registration/forgot.html')


def doctors(request):
    qs = Doctor.objects.select_related('user').filter(user__is_active=True)
    search = request.GET.get('q', '').strip()
    if search:
        qs = qs.filter(Q(user__first_name__icontains=search) | Q(user__last_name__icontains=search) | Q(specialty__icontains=search))
    return page(request, 'public/doctors.html', {'doctors': qs, 'search': search})


def doctor_detail(request, pk):
    doctor = get_object_or_404(Doctor.objects.select_related('user'), pk=pk, user__is_active=True)
    try:
        day = date.fromisoformat(request.GET.get('date', str(timezone.localdate()+timedelta(days=1))))
    except ValueError:
        day = timezone.localdate()+timedelta(days=1)
    return page(request, 'public/doctor.html', {'doctor': doctor, 'periods': doctor.availability.all(), 'day': day, 'slots': available_slots(doctor, day)})


@login_required
def dashboard(request):
    return redirect(destination(request.user))


@login_required
def patient_dashboard(request):
    if role(request.user) != 'patient':
        raise PermissionDenied
    return dashboard_page(request)


@login_required
def doctor_dashboard(request):
    if role(request.user) != 'doctor':
        raise PermissionDenied
    return dashboard_page(request)


@login_required
def doctor_schedule(request):
    if role(request.user) != 'doctor':
        raise PermissionDenied
    return page(request, 'dashboard/schedule.html', {'periods': request.user.doctor_profile.availability.all()})


def dashboard_page(request):
    qs = visible_appointments(request.user)
    now = timezone.now()
    upcoming = qs.filter(status='confirmed', starts_at__gt=now)
    return page(request, 'dashboard/index.html', {
        'appointments': upcoming[:8], 'history': qs.filter(Q(starts_at__lte=now) | Q(status='cancelled')).order_by('-starts_at')[:20],
        'upcoming_count': upcoming.count(), 'today_count': qs.filter(starts_at__date=timezone.localdate(), status='confirmed').count(),
        'cancelled_count': qs.filter(status='cancelled').count(), 'appointment_count': qs.count(),
        'periods': request.user.doctor_profile.availability.all() if role(request.user)=='doctor' else [],
    })


@login_required
def appointments(request):
    return page(request, 'dashboard/appointments.html', {'appointments': visible_appointments(request.user).order_by('-starts_at')})


@login_required
def book(request):
    if role(request.user) != 'patient':
        raise PermissionDenied
    initial = {'doctor': request.GET.get('doctor'), 'date': request.GET.get('date'), 'starts_at': request.GET.get('slot')}
    form = AppointmentForm(request.POST or None, initial=initial)
    if request.method == 'POST' and form.is_valid():
        if timezone.localtime(form.cleaned_data['starts_at']).date() != form.cleaned_data['date']:
            form.add_error('starts_at', 'The slot must match the selected date.')
        else:
            try:
                book_appointment(request.user, form.cleaned_data['doctor'], form.cleaned_data['starts_at'], form.cleaned_data['reason'])
            except (ValidationError, IntegrityError, OperationalError) as exc:
                if isinstance(exc, OperationalError) and not any(word in str(exc).lower() for word in ('locked', 'busy')):
                    raise
                form.add_error(None, '; '.join(exc.messages) if isinstance(exc, ValidationError) else 'Slot no longer available.')
            else:
                messages.success(request, 'Your appointment is confirmed.')
                return redirect('patient-dashboard')
    return page(request, 'appointments/booking.html', {'form': form})


@login_required
def appointment_detail(request, pk):
    obj = get_object_or_404(visible_appointments(request.user), pk=pk)
    error = None
    cancellation_form = CancellationForm(request.POST if request.method == 'POST' and request.POST.get('action') == 'cancelled' else None)
    if request.method == 'POST':
        if role(request.user) not in ('patient', 'administrator'):
            raise PermissionDenied
        action = request.POST.get('action')
        starts = None
        if action == 'rescheduled':
            from django.forms import DateTimeField
            try:
                starts = DateTimeField().clean(request.POST.get('starts_at'))
            except ValidationError:
                error = 'Choose an available time.'
        if action == 'cancelled' and not cancellation_form.is_valid():
            error = 'Provide a nonblank cancellation reason of at most 500 characters.'
        if not error:
            try:
                change_appointment(request.user, pk, action, starts, cancellation_reason=cancellation_form.cleaned_data['reason'] if action == 'cancelled' else None)
            except (ValidationError, IntegrityError, OperationalError) as exc:
                if isinstance(exc, OperationalError) and not any(word in str(exc).lower() for word in ('locked', 'busy')):
                    raise
                error = '; '.join(exc.messages) if isinstance(exc, ValidationError) else 'Slot no longer available.'
            else:
                messages.success(request, 'Appointment updated.')
                return redirect('appointment-detail', pk=pk)
    return page(request, 'appointments/detail.html', {'appointment': obj, 'error': error, 'cancellation_form': cancellation_form, 'can_change': role(request.user) in ('patient','administrator') and obj.status=='confirmed' and obj.starts_at>timezone.now()})


@admin_required
def platform(request):
    qs = Appointment.objects.all()
    now = timezone.now()
    days = [timezone.localdate()+timedelta(days=i) for i in range(-6, 1)]
    chart = []
    for day in days:
        chart.append({'label': day.strftime('%a'), 'count': qs.filter(starts_at__date=day).count(), 'cancelled': qs.filter(starts_at__date=day, status='cancelled').count()})
    maximum = max([v['count'] for v in chart]+[1])
    for v in chart:
        v['height'] = round(v['count']/maximum*100)
        v['cancelled_height'] = round(v['cancelled']/maximum*100)
    volumes = Doctor.objects.select_related('user').annotate(total=Count('appointments'), upcoming=Count('appointments', filter=Q(appointments__status='confirmed', appointments__starts_at__gt=now)))
    def series(field, dates, upcoming=False):
        source = qs.filter(status='confirmed', starts_at__gt=now) if upcoming else qs
        values = [{'label': day.strftime('%a'), 'count': source.filter(**{field+'__date': day}).count()} for day in dates]
        maximum = max([v['count'] for v in values]+[1])
        for value in values:
            value['height'] = round(value['count']/maximum*100)
        return values
    return page(request, 'platform/overview.html', {
        'patients_count': Patient.objects.count(), 'doctors_count': Doctor.objects.count(), 'total_count': qs.count(),
        'upcoming_count': qs.filter(starts_at__gt=now, status='confirmed').count(), 'today_count': qs.filter(starts_at__date=timezone.localdate(), status='confirmed').count(),
        'cancelled_count': qs.filter(status='cancelled').count(), 'confirmed_count': qs.filter(status='confirmed').count(),
        'doctors_booked': Doctor.objects.filter(appointments__isnull=False).distinct().count(),
        'chart': chart, 'volumes': volumes, 'events': AppointmentEvent.objects.select_related('actor', 'appointment__doctor__user')[:6],
        'booking_chart': series('created_at', days),
        'upcoming_chart': series('starts_at', [timezone.localdate()+timedelta(days=i) for i in range(7)], True),
        'recent_patients': Patient.objects.select_related('user').order_by('-user__date_joined')[:4],
        'appointments': qs.select_related('doctor__user','patient__user').filter(starts_at__gt=now, status='confirmed')[:6],
    })


@admin_required
def platform_appointments(request):
    qs = Appointment.objects.select_related('patient__user','doctor__user').all()
    q = request.GET.get('q', '').strip()
    if q:
        qs = qs.filter(Q(patient__user__first_name__icontains=q)|Q(patient__user__last_name__icontains=q)|Q(doctor__user__last_name__icontains=q)|Q(reason__icontains=q))
    for key in ('doctor','patient'):
        value = request.GET.get(key, '')
        if value.isdigit():
            qs = qs.filter(**{key+'_id': int(value)})
    if request.GET.get('status') in ('confirmed','cancelled'):
        qs = qs.filter(status=request.GET['status'])
    if request.GET.get('date'):
        try:
            qs = qs.filter(starts_at__date=date.fromisoformat(request.GET['date']))
        except ValueError:
            messages.error(request, 'Use a valid date filter.')
    return page(request, 'platform/appointments.html', {'appointments': qs.order_by('-starts_at'), 'doctors': Doctor.objects.select_related('user'), 'patients': Patient.objects.select_related('user')})


@admin_required
def platform_doctors(request):
    return page(request, 'platform/doctors.html', {'doctors': Doctor.objects.select_related('user').annotate(total=Count('appointments'))})


@admin_required
def platform_doctor(request, pk):
    obj = get_object_or_404(Doctor, pk=pk)
    form = DoctorForm(request.POST or None, instance=obj)
    if request.method=='POST' and form.is_valid():
        form.save()
        messages.success(request, 'Doctor profile updated.')
        return redirect('platform-doctors')
    return page(request, 'platform/form.html', {'form': form, 'title': str(obj), 'subtitle': 'Update profile and availability', 'periods': obj.availability.all()})


@admin_required
def platform_patients(request):
    qs = Patient.objects.select_related('user').annotate(total=Count('appointments'))
    q = request.GET.get('q', '').strip()
    if q:
        qs = qs.filter(Q(user__first_name__icontains=q)|Q(user__last_name__icontains=q)|Q(user__username__icontains=q))
    return page(request, 'platform/patients.html', {'patients': qs})


@admin_required
def platform_patient(request, pk):
    obj = get_object_or_404(Patient.objects.select_related('user'), pk=pk)
    return page(request, 'platform/patient.html', {'patient': obj, 'appointments': obj.appointments.select_related('doctor__user').order_by('-starts_at')})


@admin_required
def platform_schedules(request):
    form = ScheduleForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            Doctor.objects.select_for_update().get(pk=form.cleaned_data['doctor'].pk)
            # Revalidate under the doctor lock to serialize schedule changes.
            try:
                form.instance.full_clean()
            except ValidationError as exc:
                form.add_error(None, exc)
            else:
                form.save()
                messages.success(request, 'Working period added.')
                return redirect('platform-schedules')
    return page(request, 'platform/schedules.html', {'form': form, 'periods': DoctorAvailability.objects.select_related('doctor__user')})


@admin_required
def platform_activity(request):
    return page(request, 'platform/activity.html', {'events': AppointmentEvent.objects.select_related('actor','appointment__doctor__user')[:100], 'recent_patients': Patient.objects.select_related('user').order_by('-user__date_joined')[:20]})


@login_required
def account(request):
    return page(request, 'dashboard/account.html')
