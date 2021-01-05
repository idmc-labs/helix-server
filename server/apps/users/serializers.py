from django.contrib.auth import get_user_model, authenticate
from django.db import transaction
from django.utils.translation import gettext
from django_enumfield.contrib.drf import EnumField
from rest_framework import serializers

from apps.users.enums import USER_ROLE
from apps.users.utils import get_user_from_activation_token

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
                is_active=False
            )
        return instance


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True, write_only=True)
    password = serializers.CharField(required=True, write_only=True)

    def validate(self, attrs):
        email = attrs.get('email', '')
        if User.objects.filter(email__iexact=email, is_active=False).exists():
            raise serializers.ValidationError('Request an admin to activate your account.')
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


class UserSerializer(serializers.ModelSerializer):
    role = EnumField(USER_ROLE, required=False)

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'username', 'is_active', 'role']

    def validate_role(self, role):
        if not self.context['request'].user.has_perm('users.change_user'):
            raise serializers.ValidationError(gettext('You are not allowed to change the role.'))
        return role

    def validate(self, attrs):
        if not User.can_update_user(self.instance.id, self.context['request'].user):
            raise serializers.ValidationError(gettext('You are not allowed to update this user.'))
        return attrs

    def update(self, instance, validated_data):
        role = validated_data.pop('role', None)
        instance = super().update(instance, validated_data)
        if role is not None:
            instance.set_role(role)
        return instance
