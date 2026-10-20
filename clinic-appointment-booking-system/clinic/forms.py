from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from django.db import transaction
from .models import Doctor, DoctorAvailability, Patient

class SignInForm(AuthenticationForm):
    remember_me = forms.BooleanField(required=False)

class RegisterForm(UserCreationForm):
    first_name = forms.CharField(max_length=150)
    last_name = forms.CharField(max_length=150)
    email = forms.EmailField()
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'username', 'email', 'password1', 'password2')
    @transaction.atomic
    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save()
            Patient.objects.create(user=user)
        return user

class AppointmentForm(forms.Form):
    doctor = forms.ModelChoiceField(queryset=Doctor.objects.filter(is_available=True, user__is_active=True))
    date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    starts_at = forms.DateTimeField(widget=forms.Select(), label='Available time')
    reason = forms.CharField(max_length=200, required=False, widget=forms.Textarea(attrs={'rows': 2}))

class DoctorForm(forms.ModelForm):
    class Meta:
        model = Doctor
        fields = ('specialty', 'biography', 'is_available')

class ScheduleForm(forms.ModelForm):
    weekday = forms.TypedChoiceField(choices=enumerate(['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']), coerce=int)
    class Meta:
        model = DoctorAvailability
        fields = ('doctor', 'weekday', 'start_time', 'end_time')
        widgets = {'start_time': forms.TimeInput(attrs={'type': 'time'}), 'end_time': forms.TimeInput(attrs={'type': 'time'})}


class CancellationForm(forms.Form):
    reason = forms.CharField(max_length=500, label='Cancellation reason', widget=forms.Textarea(attrs={'rows': 3}))

    def clean_reason(self):
        from .services import validate_cancellation_reason
        return validate_cancellation_reason(self.cleaned_data['reason'])
