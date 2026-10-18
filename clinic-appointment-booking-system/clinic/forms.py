from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.utils import timezone
from .models import Appointment, Doctor, Patient

class RegisterForm(UserCreationForm):
    first_name = forms.CharField(max_length=150)
    last_name = forms.CharField(max_length=150)
    email = forms.EmailField()
    class Meta: model = User; fields = ('username','first_name','last_name','email','password1','password2')
    def save(self, commit=True):
        user = super().save(commit); user.email = self.cleaned_data['email']; user.save(); Patient.objects.get_or_create(user=user)
        return user

class AppointmentForm(forms.ModelForm):
    doctor = forms.ModelChoiceField(queryset=Doctor.objects.filter(is_available=True))
    date = forms.DateField(widget=forms.DateInput(attrs={'type':'date'}))
    time = forms.TimeField(widget=forms.TimeInput(attrs={'type':'time'}))
    class Meta: model = Appointment; fields = ('doctor','date','time','reason')
    def clean(self):
        cleaned = super().clean()
        if cleaned.get('date') and cleaned.get('time'):
            starts = timezone.make_aware(timezone.datetime.combine(cleaned['date'], cleaned['time']))
            if starts <= timezone.now() + timezone.timedelta(hours=1): raise forms.ValidationError('Choose a time at least one hour from now.')
            cleaned['starts_at'] = starts
        return cleaned
