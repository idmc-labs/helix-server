from django.contrib.auth import get_user_model, authenticate
from django import forms
from django.db import transaction
from djoser.conf import settings as djoser_settings
from rest_framework import serializers

from apps.users.utils import send_activation_email, get_user_from_activation_token

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(required=True, write_only=True)

    class Meta:
        model = User
        fields = ['email', 'first_name', 'last_name', 'username', 'password']

    def validate_email(self, email) -> str:
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError('The email is taken.')
        return email

    def save(self, **kwargs):
        with transaction.atomic():
            instance = User.objects.create_user(
                first_name=self.validated_data.get('first_name', ''),
                last_name=self.validated_data.get('last_name', ''),
                username=self.validated_data.get('username', ''),
                email=self.validated_data['email'],
                password=self.validated_data['password'],
            )
            if getattr(djoser_settings, 'SEND_ACTIVATION_EMAIL'):
                instance.is_active = False
                instance.save()
                transaction.on_commit(
                    lambda: send_activation_email(instance, self.context['request'])
                )
        return instance


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True, write_only=True)
    password = serializers.CharField(required=True, write_only=True)

    def validate(self, attrs):
        email = attrs.get('email', '')
        if User.objects.filter(email__iexact=email, is_active=False).exists():
            raise serializers.ValidationError('Please activate your account first.')
        user = authenticate(email=email,
                            password=attrs.get('password', ''))
        if not user:
            raise serializers.ValidationError('Invalid Email or Password.')
        attrs.update(dict(user=user))
        return attrs


class ActivateSerializer(serializers.Serializer):
    uid = serializers.CharField(required=True, write_only=True)
    token = serializers.CharField(required=True, write_only=True)

    def validate(self, attrs):
        user = get_user_from_activation_token(uid=attrs.get('uid', ''),
                                              token=attrs.get('token', ''))
        if user is None:
            raise serializers.ValidationError('Activation link is not valid.')
        user.is_active = True
        user.save()
        return attrs

