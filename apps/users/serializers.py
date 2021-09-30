from django.utils import timezone
import time
from django.contrib.auth import get_user_model, authenticate
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.db import transaction
from django.conf import settings
from djoser.utils import encode_uid
from django.utils.translation import gettext
from rest_framework import serializers

from apps.users.enums import USER_ROLE
from apps.users.utils import get_user_from_activation_token
from apps.users.models import Portfolio
from apps.country.models import MonitoringSubRegion, Country
from apps.contrib.serializers import UpdateSerializerMixin, IntegerIDField
from utils.validations import validate_hcaptcha, MissingCaptchaException

from .tasks import send_email, recalculate_user_roles

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
                now = time.mktime(timezone.now().timetuple())
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
            raise serializers.ValidationError(gettext('Request an admin to activate your account.'))
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
            raise serializers.ValidationError(gettext('Activation link is not valid.'))
        user.is_active = True
        user.save()
        return attrs


# Begin Portfolios


class MonitoringExpertPortfolioSerializer(serializers.ModelSerializer):
    country = serializers.PrimaryKeyRelatedField(queryset=Country.objects.all(), required=True)

    def validate(self, attrs: dict) -> dict:
        attrs['role'] = USER_ROLE.MONITORING_EXPERT
        return attrs

    class Meta:
        model = Portfolio
        fields = ['user', 'country']


class BulkMonitoringExpertPortfolioSerializer(serializers.Serializer):
    portfolios = MonitoringExpertPortfolioSerializer(many=True)
    region = serializers.PrimaryKeyRelatedField(
        queryset=MonitoringSubRegion.objects.all()
    )

    def _validate_region_countries(self, attrs: dict) -> None:
        # check if all the provided countries belong to the region
        portfolios = attrs.get('portfolios', [])
        regions = set([portfolio['country'].monitoring_sub_region for portfolio in portfolios])
        if len(regions) > 1:
            raise serializers.ValidationError('Multiple regions are not allowed', code='multiple-regions')
        if len(regions) and list(regions)[0] != attrs['region']:
            raise serializers.ValidationError('Countries are not part of the region', code='region-mismatch')

    def _validate_can_add(self, attrs: dict) -> None:
        if self.context['request'].user.highest_role == USER_ROLE.ADMIN:
            return
        if self.context['request'].user.highest_role not in [USER_ROLE.REGIONAL_COORDINATOR]:
            raise serializers.ValidationError(
                gettext('You are not allowed to perform this action'),
                code='not-allowed'
            )
        portfolio = Portfolio.get_coordinator(
            ms_region=attrs['region']
        )
        if portfolio is None or self.context['request'].user != portfolio.user:
            raise serializers.ValidationError(
                gettext('You are not allowed to add to this region'),
                code='not-allowed-in-region'
            )

    def validate(self, attrs: dict) -> dict:
        self._validate_can_add(attrs)
        self._validate_region_countries(attrs)
        return attrs

    def save(self, *args, **kwargs):
        with transaction.atomic():
            reset_user_roles_for = []
            for portfolio in self.validated_data['portfolios']:
                instance = Portfolio.objects.get(country=portfolio['country'],
                                                 role=USER_ROLE.MONITORING_EXPERT)
                old_user = instance.user
                instance.user = portfolio['user']
                instance.save()
                if portfolio['user'] != old_user:
                    reset_user_roles_for.append(old_user.pk)
            recalculate_user_roles.delay(reset_user_roles_for)


class RegionalCoordinatorPortfolioSerializer(serializers.ModelSerializer):
    def _validate_can_add(self) -> None:
        if self.context['request'].user.highest_role != USER_ROLE.ADMIN:
            raise serializers.ValidationError(
                gettext('You are not allowed to perform this action'),
                code='not-allowed'
            )

    def validate(self, attrs: dict) -> dict:
        self._validate_can_add()
        attrs['role'] = USER_ROLE.REGIONAL_COORDINATOR
        self.instance = Portfolio.objects.get(
            monitoring_sub_region=attrs['monitoring_sub_region'],
            role=USER_ROLE.REGIONAL_COORDINATOR,
        )
        return attrs

    def save(self):
        instance = super().save()
        recalculate_user_roles.delay([self.instance.user.pk])
        return instance

    class Meta:
        model = Portfolio
        fields = ['user', 'monitoring_sub_region']
        extra_kwargs = {
            'monitoring_sub_region': dict(required=True, allow_null=False),
        }


class AdminPortfolioSerializer(serializers.Serializer):
    register = serializers.BooleanField(required=True)
    user = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())

    def _validate_unique(self, attrs) -> None:
        if attrs['register'] and Portfolio.objects.filter(
            user=attrs.get('user'),
            role=USER_ROLE.ADMIN,
        ).exclude(
            id=getattr(self.instance, 'id', None)
        ).exists():
            raise serializers.ValidationError(gettext(
                'Portfolio already exists'
            ), code='already-exists')

    def _validate_is_admin(self) -> None:
        if not self.context['request'].user.highest_role == USER_ROLE.ADMIN:
            raise serializers.ValidationError(
                gettext('You are not allowed to perform this action'),
                code='not-allowed'
            )

    def validate(self, attrs: dict) -> dict:
        self._validate_is_admin()
        self._validate_unique(attrs)

        return attrs

    def save(self):
        if self.validated_data['register']:
            Portfolio.objects.create(
                user=self.validated_data['user'],
                role=USER_ROLE.ADMIN
            )
        else:
            p = Portfolio.objects.get(
                user=self.validated_data['user'],
                role=USER_ROLE.ADMIN
            )
            p.delete()

        return self.validated_data['user']


# End Portfolios


class UserSerializer(UpdateSerializerMixin, serializers.ModelSerializer):
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

    def update(self, instance, validated_data):
        instance = super().update(instance, validated_data)
        portfolios = validated_data.get('portfolios', [])
        if portfolios:
            Portfolio.objects.bulk_create([
                Portfolio(**item, user=instance) for item in portfolios
            ])

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
