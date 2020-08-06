from django.contrib.auth import get_user_model, authenticate
from django import forms

User = get_user_model()


class LoginForm(forms.Form):
    email = forms.EmailField(required=True)
    password = forms.CharField(required=True)

    def clean(self):
        ret = super().clean()
        user = authenticate(email=self.cleaned_data['email'],
                            password=self.cleaned_data['password'])
        if not user:
            raise forms.ValidationError("Invalid Email or Password")
        ret.update(dict(user=user))
        return ret

    def save(self):
        return
