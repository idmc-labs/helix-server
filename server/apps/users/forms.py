from django.contrib.auth import get_user_model, authenticate
from django import forms
from django.contrib.auth.tokens import default_token_generator
from django.db import transaction
from djoser.conf import settings as djoser_settings
from djoser.utils import decode_uid

from apps.users.utils import send_activation_email, activation_token_is_valid

User = get_user_model()


class RegisterForm(forms.ModelForm):
    password1 = forms.CharField(required=True)
    password2 = forms.CharField(required=True)

    class Meta:
        model = User
        fields = ['email', 'first_name', 'last_name', 'username']

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        super(RegisterForm, self).__init__(*args, **kwargs)

    def clean_email(self):
        if User.objects.filter(email=self.cleaned_data['email']).exists():
            raise forms.ValidationError('Email already exists.')
        return self.cleaned_data['email']

    def clean_password2(self):
        password1 = self.cleaned_data['password1']
        password2 = self.cleaned_data['password2']
        if password1 != password2:
            raise forms.ValidationError('Passwords do not match.')

    def save(self, commit=True):
        super().save(commit=False)
        with transaction.atomic():
            instance = User.objects.create_user(
                first_name=self.cleaned_data['first_name'],
                last_name=self.cleaned_data['last_name'],
                username=self.cleaned_data['username'],
                email=self.cleaned_data['email'],
                password=self.cleaned_data['password1'],
            )
            if getattr(djoser_settings, 'SEND_ACTIVATION_EMAIL'):
                instance.is_active = False
                instance.save()
                send_activation_email(instance, self.request)
        return instance


class LoginForm(forms.Form):
    email = forms.EmailField(required=True)
    password = forms.CharField(required=True)

    def clean(self):
        cleaned_data = super().clean()
        user = authenticate(email=(email := self.cleaned_data['email']),
                            password=self.cleaned_data['password'])
        if not user and User.objects.filter(email=email).exists():
            raise forms.ValidationError('Please activate your account first.')
        if not user:
            raise forms.ValidationError("Invalid Email or Password.")
        cleaned_data.update(dict(user=user))
        return cleaned_data

    def save(self):
        return


class ActivateForm(forms.Form):
    uid = forms.CharField()
    token = forms.CharField()

    def clean(self):
        if not (user := activation_token_is_valid(uid=self.cleaned_data['uid'],
                                                  token=self.cleaned_data['token'])):
            raise forms.ValidationError('Activation link is not valid.')
        user.is_active = True
        user.save()

    def save(self):
        pass
