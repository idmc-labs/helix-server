from django.contrib.auth import get_user_model, authenticate
from django import forms
from django.db import transaction
from djoser.conf import settings as djoser_settings
from rest_framework import serializers

from apps.users.utils import send_activation_email, activation_token_is_valid

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    password1 = serializers.CharField(required=True, write_only=True)
    password2 = serializers.CharField(required=True, write_only=True)

    class Meta:
        model = User
        fields = ['email', 'first_name', 'last_name', 'username', 'password1',
                  'password2']

    def validate_email(self, email):
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('Email already exists.')
        return email

    def validate_password2(self, password2):
        password1 = self.initial_data.get('password1', None)
        if password1 is None:
            return
        if password1 != password2:
            raise forms.ValidationError('Passwords do not match.')
        return password2

    def save(self, **kwargs):
        with transaction.atomic():
            instance = User.objects.create_user(
                first_name=self.validated_data.get('first_name', ''),
                last_name=self.validated_data.get('last_name', ''),
                username=self.validated_data.get('username', ''),
                email=self.validated_data['email'],
                password=self.validated_data['password1'],
            )
            if getattr(djoser_settings, 'SEND_ACTIVATION_EMAIL'):
                instance.is_active = False
                instance.save()
                # send_activation_email(instance, self.context['request'])
                transaction.on_commit(
                    lambda: send_activation_email(instance, self.context['request'])
                )
        return instance


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True, write_only=True)
    password = serializers.CharField(required=True, write_only=True)

    def validate(self, attrs):
        user = authenticate(email=(email := attrs.get('email', '')),
                            password=attrs.get('password', ''))
        if not user and User.objects.filter(email=email).exists():
            raise serializers.ValidationError('Please activate your account first.')
        if not user:
            raise serializers.ValidationError("Invalid Email or Password.")
        attrs.update(dict(user=user))
        return attrs

    def save(self, **kwargs):
        pass


class ActivateSerializer(serializers.Serializer):
    uid = serializers.CharField(required=True, write_only=True)
    token = serializers.CharField(required=True, write_only=True)

    def validate(self, attrs):
        if not (user := activation_token_is_valid(uid=attrs.get('uid', ''),
                                                  token=attrs.get('token', ''))):
            raise serializers.ValidationError('Activation link is not valid.')
        user.is_active = True
        user.save()
        return attrs

    def save(self):
        pass
