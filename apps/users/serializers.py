from datetime import datetime
import time

from django.contrib.auth import get_user_model, authenticate
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from django.conf import settings
from django.utils.translation import gettext
from rest_framework import serializers

from apps.users.enums import USER_ROLE
from apps.users.utils import get_user_from_activation_token
from apps.users.models import Portfolio
from apps.contrib.serializers import UpdateSerializerMixin, IntegerIDField
from utils.validations import validate_hcaptcha, MissingCaptchaException

User = get_user_model()


class UserPasswordSerializer(serializers.ModelSerializer):
    old_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(required=True, write_only=True)

    class Meta:
        model = User
        fields = ['old_password', 'new_password']

    def validate_old_password(self, password) -> str:
        if not self.instance.check_password(password):
            raise serializers.ValidationError(gettext('Invalid Password'))
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
            raise serializers.ValidationError(gettext('The email is taken.'))
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
            raise serializers.ValidationError(gettext('Request an admin to activate your account.'))
        user = authenticate(email=email,
                            password=attrs.get('password', ''))
        if not user:
            attempts = User._get_login_attempt(email)
            User._set_login_attempt(email, attempts + 1)
            raise serializers.ValidationError(gettext('Invalid Email or Password.'))
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
            raise serializers.ValidationError(gettext('Activation link is not valid.'))
        user.is_active = True
        user.save()
        return attrs


class PortfolioSerializer(serializers.ModelSerializer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if hasattr(self, 'initial_data'):
            self.initial_data['monitoring_sub_region'] = self.initial_data.get('monitoring_sub_region')

    def validate_user(self, user):
        # During update we will not allow changing the user
        if self.instance:
            return self.instance.user
        return user

    def _validate_role_by_authenticated_user_role(self, attrs: dict) -> None:
        # we cannot set a role higher than ourself
        role = attrs.get('role')
        authenticated_user = self.context['request'].user
        highest_role = authenticated_user.highest_role
        # though already handled in mutations
        if highest_role not in [USER_ROLE.REGIONAL_COORDINATOR, USER_ROLE.ADMIN]:
            raise serializers.ValidationError(
                gettext('You cannot perform this action'),
                code='not-allowed'
            )
        if highest_role == USER_ROLE.REGIONAL_COORDINATOR and role in [
                USER_ROLE.ADMIN
        ]:
            raise serializers.ValidationError({
                'role': gettext(
                    'You are not allowed to set an admin.'
                )
            }, code='role-not-set')

        # we cannot change our own role
        if authenticated_user == attrs.get('user'):
            raise serializers.ValidationError({
                'role': gettext(
                    'Please ask another admin or regional coordinator'
                )
            }, code='cannot-modify-yourself')

    def _validate_role_region(self, attrs) -> None:
        role = attrs.get('role')
        monitoring_sub_region = attrs.get('monitoring_sub_region') or getattr(self.instance, 'monitoring_sub_region', None)
        if role in [USER_ROLE.ADMIN, USER_ROLE.GUEST] and monitoring_sub_region:
            raise serializers.ValidationError(gettext(
                'Monitoring region is not allowed with given role'
            ))
        if role in [USER_ROLE.MONITORING_EXPERT, USER_ROLE.REGIONAL_COORDINATOR] and not monitoring_sub_region:
            raise serializers.ValidationError({
                'monitoring_sub_region': gettext(
                    'This field is required'
                )
            }, code='required')

        user = self.context['request'].user
        # highest role here can only be either regional coordinator or admin
        highest_role = user.highest_role
        if highest_role == USER_ROLE.REGIONAL_COORDINATOR:
            if not user.portfolios.filter(
                role=USER_ROLE.REGIONAL_COORDINATOR,
                monitoring_sub_region=monitoring_sub_region
            ).exists():
                raise serializers.ValidationError({
                    'monitoring_sub_region': gettext(
                        'You are not allowed to add in this monitoring region'
                    )
                })

    def _validate_unique_together(self, attrs) -> None:
        if Portfolio.objects.filter(
            user=attrs.get('user') or getattr(self.instance, 'user', None),
            role=attrs.get('role') or getattr(self.instance, 'role', None),
            monitoring_sub_region=attrs.get('monitoring_sub_region') or getattr(self.instance, 'monitoring_sub_region', None),  # noqa
        ).exclude(id=getattr(self.instance, 'id', None)):
            raise serializers.ValidationError(gettext('This portfolio already exists.'))

    def _validate_disallow_redundant_role(self, attrs) -> None:
        user = attrs.get('user') or getattr(self.instance, 'user', None)
        monitoring_sub_region = attrs.get('monitoring_sub_region') or getattr(self.instance, 'monitoring_sub_region', None)
        if user.portfolios.count() and monitoring_sub_region == USER_ROLE.GUEST:
            raise serializers.ValidationError(
                gettext('Guest portfolio is not important for this user')
            )

    def validate(self, attrs) -> dict:
        self._validate_role_by_authenticated_user_role(attrs)
        self._validate_role_region(attrs)
        self._validate_unique_together(attrs)
        self._validate_disallow_redundant_role(attrs)
        return attrs

    class Meta:
        model = Portfolio
        fields = '__all__'
        extra_kwargs = dict(
            monitoring_sub_region=dict(required=False)
        )


class PortfolioUpdateSerializer(PortfolioSerializer):
    id = IntegerIDField(required=True)

    class Meta:
        model = Portfolio
        fields = ['id', 'role', 'monitoring_sub_region']
        extra_kwargs = dict(
            monitoring_sub_region=dict(required=False)
        )


class UserSerializer(UpdateSerializerMixin, serializers.ModelSerializer):
    # portfolios = PortfolioSerializer(many=True)
    id = IntegerIDField(required=True)

    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'username', 'is_active']

    def validate_is_active(self, is_active):
        if self.instance and self.context['request'].user == self.instance:
            raise serializers.ValidationError(gettext('You cannot activate/deactivate yourself.'))
        return is_active

    def validate(self, attrs):
        if not User.can_update_user(self.instance.id, self.context['request'].user):
            raise serializers.ValidationError(gettext('You are not allowed to update this user.'))
        return attrs
