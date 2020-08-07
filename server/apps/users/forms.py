from django.conf import settings
from django.contrib.auth import get_user_model, authenticate
from django import forms

User = get_user_model()


class RegisterForm(forms.ModelForm):
    password1 = forms.CharField(required=True)
    password2 = forms.CharField(required=True)

    class Meta:
        model = User
        fields = ['email', 'first_name', 'last_name', 'username']

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
        instance = User.objects.create_user(
            first_name=self.cleaned_data['first_name'],
            last_name=self.cleaned_data['last_name'],
            username=self.cleaned_data['username'],
            email=self.cleaned_data['email'],
            password=self.cleaned_data['password1'],
        )
        # if settings.get('SEND_ACTIVATION_EMAIL'):
        #     instance.is_active = False
        #     send_activation_email()
        #     instance.save()
        return instance


class LoginForm(forms.Form):
    email = forms.EmailField(required=True)
    password = forms.CharField(required=True)

    def clean(self):
        cleaned_data = super().clean()
        user = authenticate(email=self.cleaned_data['email'],
                            password=self.cleaned_data['password'])
        if not user:
            raise forms.ValidationError("Invalid Email or Password")
        cleaned_data.update(dict(user=user))
        return cleaned_data

    def save(self):
        return
