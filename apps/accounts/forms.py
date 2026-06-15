from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import get_user_model

from apps.accounts.models import Cohort

User = get_user_model()


class StudentSignUpForm(UserCreationForm):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'name@kepler.ac.rw'
        })
    )
    student_id = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g. KPL-BA-2025-001'
        })
    )
    cohort = forms.ModelChoiceField(
        queryset=Cohort.objects.all().order_by('-year'),
        required=False,
        empty_label='— Select your cohort —',
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('email', 'student_id', 'cohort', 'password1', 'password2')

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('This email is already registered.')
        return email

    def clean_student_id(self):
        sid = self.cleaned_data['student_id'].strip().upper()
        if User.objects.filter(student_id__iexact=sid).exists():
            raise forms.ValidationError('This student ID is already registered.')
        return sid

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email'].strip().lower()
        user.student_id = self.cleaned_data['student_id'].strip().upper()
        user.username = user.email
        user.is_active = False
        user.is_email_verified = False
        user.cohort = self.cleaned_data.get('cohort')
        user.is_cohort_confirmed = False
        if commit:
            user.save()
        return user


class EmailOrStudentIDAuthenticationForm(AuthenticationForm):
    username = forms.CharField(
        label='Email or Student ID',
        widget=forms.TextInput(attrs={
            'autofocus': True,
            'class': 'form-control',
            'placeholder': 'Email or Student ID'
        }),
    )
    password = forms.CharField(
        label='Password',
        strip=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Password'
        }),
    )