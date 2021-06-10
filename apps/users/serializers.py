from datetime import datetime
import time

from django.contrib.auth import get_user_model, authenticate
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from django.conf import settings
from django.utils.translation import gettext
from django_enumfield.contrib.drf import EnumField
from rest_framework import serializers
from django.utils import timezone
from django.core.cache import cache

from apps.users.enums import USER_ROLE
from apps.users.utils import get_user_from_activation_token
from apps.contrib.serializers import UpdateSerializerMixin, IntegerIDField
from utils.validations import validate_hcaptcha, MissingCaptchaException
from .tasks import send_email
from .utils import encode_reset_password_token, decode_reset_password_token
User = get_user_model()


class UserPasswordSerializer(serializers.ModelSerializer):
    old_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(required=True, write_only=True)

    class Meta:
        model = User
        fields = ['old_password', 'new_password']

    def validate_old_password(self, password) -> str:
        if not self.instance.check_password(password):
            raise serializers.ValidationError('Invalid Password')
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
            raise serializers.ValidationError('The email is taken.')
        return email

    def validate_captcha(self, captcha):
        if not validate_hcaptcha(captcha, self.initial_data.get('site_key', '')):
            raise serializers.ValidationError(dict(
                captcha=gettext('Invalid captcha')
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
                        gettext('Please try again in %s minute(s)') % settings.LOGIN_TIMEOUT
                    )
                elapsed = now - last_tried
                if elapsed < settings.LOGIN_TIMEOUT * 60:
                    raise serializers.ValidationError(
                        gettext('Please wait %s seconds.') % (60 - int(elapsed))
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
                captcha=gettext('Invalid captcha')
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
            raise serializers.ValidationError('Invalid Email or Password.')
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
                captcha=gettext('Invalid captcha')
            ))

    def validate(self, attrs):
        email = attrs.get("email", None)
        # if user exists for this email
        try:
            user = User.objects.get(email=email)
            code = encode_reset_password_token(user.id)
            # Store token in cache, set timeout 24 hrous
            cache.set(f"reset-password-token-{user.id}", code, 24 * 60 * 60)
            base_url = settings.FRONTEND_BASE_URL
            # Get base url by profile type
            button_url = f"{base_url}/reset-password/?password_reset_token={code}"
            message = gettext(
                "We received a request to reset your Helix account password. "
                "If you wish to do so, please click below. Otherwise, you may "
                "safely disregard this email."
            )
        # if no user exists for this email
        except User.DoesNotExist:
            # explanatory email message
            raise serializers.ValidationError(gettext('User with this email does not exists.'))
        subject = gettext("Reset password request for Helix")
        context = {
            "heading": gettext("Reset Password"),
            "message": message,
            "button_text": gettext("Reset Password"),
        }
        if button_url:
            context["button_url"] = button_url
        transaction.on_commit(lambda: send_email(
            subject, message, [email], html_context=context
        ))
        return attrs


class ResetPasswordSerializer(serializers.Serializer):
    """
    Serializer for password reset endpoints.
    """

    password_reset_token = serializers.CharField(write_only=True, required=True)
    new_password = serializers.CharField(write_only=True, required=True)

    def validate(self, attrs):
        password_reset_token = attrs.get("password_reset_token")
        user_id, token_expiry_time = None, None
        invalid_token_message = gettext('Invalid token supplied')
        expired_token_message = gettext('Token might be expired (24 hrous)')
        # Decode token and parse token created time
        decoded_data = decode_reset_password_token(password_reset_token)
        user_id, token_expiry_time = decoded_data['user_id'], decoded_data['token_expiry_time']
        if user_id and token_expiry_time:
            # Check if user exists
            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                # explanatory email message
                raise serializers.ValidationError(invalid_token_message)
            # Get token from cache
            original_token = cache.get(f"reset-password-token-{user.id}")
            if password_reset_token != original_token:
                raise serializers.ValidationError(invalid_token_message)
            # Check if token expired
            if timezone.now() > token_expiry_time:
                raise serializers.ValidationError(expired_token_message)
            # check new password and confirmation match
            new_password = attrs["new_password"]
            # set_password also hashes the password that the user will get
            user.set_password(new_password)
            user.save()
            # Delete token from cache after reset password
            # Ensure password reset link should be used only one time
            cache.delete(f"reset-password-token-{user.id}")
            return attrs
        raise serializers.ValidationError(invalid_token_message)
