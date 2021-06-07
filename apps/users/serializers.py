from datetime import datetime
import time
from django.contrib.auth import get_user_model, authenticate
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from django.conf import settings
from django.utils.translation import gettext
from django_enumfield.contrib.drf import EnumField
from rest_framework import serializers

from apps.users.enums import USER_ROLE
from apps.users.utils import get_user_from_activation_token
from apps.users.models import Portfolio
from apps.contrib.serializers import UpdateSerializerMixin, IntegerIDField
from utils.validations import validate_hcaptcha, MissingCaptchaException
from .tasks import send_email
from django.contrib.auth.tokens import default_token_generator
from djoser.utils import encode_uid

User = get_user_model()


class UserPasswordSerializer(serializers.ModelSerializer):
    old_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(required=True, write_only=True)

    class Meta:
        model = User
        fields = ['old_password', 'new_password']

    def validate_old_password(self, password) -> str:
        if not self.instance.check_password(password):
            raise serializers.ValidationError('The password is invalid.')
        return password

    def validate_new_password(self, password) -> str:
        validate_password(password)
        return password

    def save(self, **kwargs):
        self.instance.set_password(self.validated_data['new_password'])
        self.instance.save()


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(required=True, write_only=True)
    captcha = serializers.CharField(required=True, write_only=True)
    site_key = serializers.CharField(required=True, write_only=True)

    class Meta:
        model = User
        fields = ['email', 'first_name', 'last_name', 'password', 'captcha', 'site_key']

    def validate_password(self, password) -> str:
        validate_password(password)
        return password

    def validate_email(self, email) -> str:
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError('The email is already taken.')
        return email

    def validate_captcha(self, captcha):
        if not validate_hcaptcha(captcha, self.initial_data.get('site_key', '')):
            raise serializers.ValidationError(dict(
                captcha=gettext('The captcha is invalid.')
            ))

    def save(self, **kwargs):
        with transaction.atomic():
            instance = User.objects.create_user(
                first_name=self.validated_data.get('first_name', ''),
                last_name=self.validated_data.get('last_name', ''),
                username=self.validated_data['email'],
                email=self.validated_data['email'],
                password=self.validated_data['password'],
                is_active=False
            )
        return instance


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True, write_only=True)
    password = serializers.CharField(required=True, write_only=True)
    captcha = serializers.CharField(required=False, allow_null=True, write_only=True)
    site_key = serializers.CharField(required=False, allow_null=True, write_only=True)

    def _validate_captcha(self, attrs):
        captcha = attrs.get('captcha')
        site_key = attrs.get('site_key')
        email = attrs.get('email')
        attempts = User._get_login_attempt(email)

        def throttle_login_attempt():
            if attempts >= settings.MAX_CAPTCHA_LOGIN_ATTEMPTS:
                now = time.mktime(datetime.now().timetuple())
                last_tried = User._get_last_login_attempt(email)
                if not last_tried:
                    User._set_last_login_attempt(email, now)
                    raise serializers.ValidationError(
                        gettext('Please try again in %s seconds.') % settings.LOGIN_TIMEOUT
                    )
                elapsed = now - last_tried
                if elapsed < settings.LOGIN_TIMEOUT:
                    raise serializers.ValidationError(
                        gettext('Please try again in %s seconds.') % (settings.LOGIN_TIMEOUT - int(elapsed))
                    )
                else:
                    # reset
                    User._reset_login_cache(email)

        if attempts >= settings.MAX_LOGIN_ATTEMPTS and not captcha:
            raise MissingCaptchaException()
        if attempts >= settings.MAX_LOGIN_ATTEMPTS and captcha and not validate_hcaptcha(captcha, site_key):
            attempts = User._get_login_attempt(email)
            User._set_login_attempt(email, attempts + 1)

            throttle_login_attempt()
            raise serializers.ValidationError(dict(
                captcha=gettext('The captcha is invalid.')
            ))

    def validate(self, attrs):
        self._validate_captcha(attrs)

        email = attrs.get('email', '')
        if User.objects.filter(email__iexact=email, is_active=False).exists():
            raise serializers.ValidationError('Request an admin to activate your account.')
        user = authenticate(email=email,
                            password=attrs.get('password', ''))
        if not user:
            attempts = User._get_login_attempt(email)
            User._set_login_attempt(email, attempts + 1)
            raise serializers.ValidationError('The email or password is invalid.')
        attrs.update(dict(user=user))
        User._reset_login_cache(email)
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


class PortfolioSerializer(serializers.ModelSerializer):
    role = EnumField(USER_ROLE, required=True)
    id = IntegerIDField(required=False)

    def _validate_role_region(self, attrs) -> None:
        role = attrs.get('role')
        monitoring_sub_region = attrs.get('monitoring_sub_region')
        if role in [USER_ROLE.ADMIN, USER_ROLE.GUEST] and monitoring_sub_region:
            raise serializers.ValidationError(gettext(
                'Monitoring region is not allowed with given role'
            ))

    def validate(self, attrs) -> dict:
        self._validate_role_region(attrs)
        return attrs

    class Meta:
        model = Portfolio
        fields = ['id', 'role', 'monitoring_sub_region']


class UserSerializer(UpdateSerializerMixin, serializers.ModelSerializer):
    role = EnumField(USER_ROLE, required=False)
    id = IntegerIDField(required=True)

    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'username', 'is_active', 'role']

    def validate_role(self, role):
        if not self.context['request'].user.has_perm('users.change_user'):
            raise serializers.ValidationError(gettext('You are not allowed to change the role.'))
        if self.instance and self.context['request'].user == self.instance and not \
                self.instance.check_role(role):
            raise serializers.ValidationError(gettext('You are not allowed to change your role.'))
        return role

    def validate_is_active(self, is_active):
        if self.instance and self.context['request'].user == self.instance:
            raise serializers.ValidationError(gettext('You cannot activate/deactivate yourself.'))
        return is_active

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


class GenerateResetPasswordTokenSerializer(serializers.Serializer):
    """
    Serializer for password forgot endpoint.
    """
    captcha = serializers.CharField(required=True, write_only=True)
    email = serializers.EmailField(write_only=True, required=True)
    site_key = serializers.CharField(required=True, write_only=True)

    def validate_captcha(self, captcha):
        if not validate_hcaptcha(captcha, self.initial_data.get('site_key', '')):
            raise serializers.ValidationError(dict(
                captcha=gettext('The captcha is invalid.')
            ))

    def validate(self, attrs):
        email = attrs.get("email", None)
        # if user exists for this email
        try:
            user = User.objects.get(email=email)
            # Generate password reset token and uid
            token = default_token_generator.make_token(user)
            uid = encode_uid(user.pk)
            # Get base url by profile type
            button_url = settings.PASSWORD_RESET_CLIENT_URL.format(
                uid=uid,
                token=token,
            )
            message = gettext(
                "We received a request to reset your Helix account password. "
                "If you wish to do so, please click below. Otherwise, you may "
                "safely disregard this email."
            )
        # if no user exists for this email
        except User.DoesNotExist:
            # explanatory email message
            raise serializers.ValidationError(gettext('User with this email does not exist.'))
        subject = gettext("Reset password request for Helix")
        context = {
            "heading": gettext("Reset Password"),
            "message": message,
            "button_text": gettext("Reset Password"),
        }
        if button_url:
            context["button_url"] = button_url
        transaction.on_commit(lambda: send_email.delay(
            subject, message, [email], html_context=context
        ))
        return attrs


class ResetPasswordSerializer(serializers.Serializer):
    """
    Serializer for password reset endpoints.
    """

    password_reset_token = serializers.CharField(write_only=True, required=True)
    uid = serializers.CharField(write_only=True, required=True)
    new_password = serializers.CharField(write_only=True, required=True)

    def validate_new_password(self, password):
        validate_password(password)
        return password

    def validate(self, attrs):
        uid = attrs.get("uid", None)
        token = attrs.get("password_reset_token", None)
        new_password = attrs.get("new_password", None)
        user = get_user_from_activation_token(uid, token)
        if user is None:
            raise serializers.ValidationError(gettext('The token is invalid.'))
        # set_password also hashes the password that the user will get
        user.set_password(new_password)
        user.save()
        return attrs
