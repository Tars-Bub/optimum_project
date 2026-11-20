from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from .models import Profile

User = get_user_model()


class RegisterForm(forms.Form):
    full_name = forms.CharField(max_length=100)
    position = forms.CharField(max_length=60, required=False)
    email = forms.EmailField()
    contact = forms.CharField(max_length=30, required=False)
    username = forms.CharField(max_length=30)
    password1 = forms.CharField(widget=forms.PasswordInput, label='Password')
    password2 = forms.CharField(widget=forms.PasswordInput, label='Confirm password')

    def clean_username(self):
        username = self.cleaned_data['username'].strip()
        if User.objects.filter(username__iexact=username).exists():
            raise ValidationError('That username is already taken.')
        return username

    def clean(self):
        data = super().clean()
        p1, p2 = data.get('password1'), data.get('password2')
        if p1 and p2 and p1 != p2:
            self.add_error('password2', 'Passwords do not match.')
        elif p1:
            try:
                validate_password(p1)
            except ValidationError as exc:
                self.add_error('password1', exc)
        return data


class StaffForm(forms.Form):
    """Admin adds or edits a staff account. Username and password only when adding."""
    full_name = forms.CharField(max_length=100)
    position = forms.CharField(max_length=60, required=False)
    email = forms.EmailField()
    contact = forms.CharField(max_length=30, required=False)
    username = forms.CharField(max_length=30)
    role = forms.ChoiceField(choices=Profile.ROLE_CHOICES)
    password = forms.CharField(widget=forms.PasswordInput, label='Temporary password')

    def __init__(self, *args, editing=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.editing = editing
        if editing:
            del self.fields['username']
            del self.fields['password']

    def clean_username(self):
        username = self.cleaned_data['username'].strip()
        if User.objects.filter(username__iexact=username).exists():
            raise ValidationError('That username is already taken.')
        return username

    def clean_password(self):
        password = self.cleaned_data['password']
        validate_password(password)
        return password
