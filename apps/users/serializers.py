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
from apps.country.models import Country
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
    def _validate_country_is_not_occupied(self, attrs: dict) -> None:
        portfolios = Portfolio.objects.filter(
            role=USER_ROLE.MONITORING_EXPERT,
            countries__in=attrs.get('countries', []),
        ).exclude(
            id=getattr(self.instance, 'id', None)
        )
        if portfolios.exists():
            countries = Country.objects.filter(
                id__in=portfolios.values('countries')
            )
            raise serializers.ValidationError(
                gettext('Following countries already have monitoring experts: %s')
                % ' | '.join(c.name for c in countries),
                code='already-occupied'
            )

    def _validate_can_add(self, attrs: dict) -> None:
        if self.context['request'].user.highest_role not in [USER_ROLE.REGIONAL_COORDINATOR]:
            raise serializers.ValidationError(
                gettext('You are not allowed to perform this action'),
                code='not-allowed'
            )
        portfolio = Portfolio.get_coordinator(
            ms_region=attrs['monitoring_sub_region']
        )
        if portfolio is None or self.context['request'].user != portfolio.user:
            raise serializers.ValidationError(
                gettext('You are not allowed to add to this region'),
                code='not-allowed-in-region'
            )

    def _validate_unique_monitoring_expert_per_user(self, attrs: dict):
        # one user can only have one monitoring expert role
        if Portfolio.objects.filter(
            user=attrs.get('user'),
            monitoring_sub_region=attrs.get('monitoring_sub_region'),
            role=USER_ROLE.MONITORING_EXPERT,
        ).exclude(
            id=getattr(self.instance, 'id', None)
        ).exists():
            raise serializers.ValidationError(
                gettext('Monitoring expert portfolio for this region already exists.'),
                code='duplicate-portfolio'
            )

    def validate(self, attrs: dict) -> dict:
        self._validate_can_add(attrs)
        self._validate_country_is_not_occupied(attrs)
        self._validate_unique_monitoring_expert_per_user(attrs)
        attrs['role'] = USER_ROLE.MONITORING_EXPERT
        return attrs

    class Meta:
        model = Portfolio
        fields = ['user', 'countries', 'monitoring_sub_region']
        extra_kwargs = {
            'monitoring_sub_region': dict(required=True, allow_null=False),
            'countries': dict(required=True),
        }


class RegionalCoordinatorPortfolioSerializer(serializers.ModelSerializer):
    def _validate_monitoring_region_already_occupied(self, attrs: dict) -> None:
        if portfolio := Portfolio.objects.filter(
            role=USER_ROLE.REGIONAL_COORDINATOR,
            monitoring_sub_region=attrs['monitoring_sub_region'].id,
        ).exclude(id=getattr(self.instance, 'id', None)):
            raise serializers.ValidationError(
                gettext('This monitoring region is already occupied by %s')
                % portfolio.get().user.full_name,
                code='already-occupied'
            )

    def _validate_can_add(self) -> None:
        if not self.context['request'].user.highest_role == USER_ROLE.ADMIN:
            raise serializers.ValidationError(
                gettext('You are not allowed to perform this action'),
                code='not-allowed'
            )

    def validate(self, attrs: dict) -> dict:
        self._validate_monitoring_region_already_occupied(attrs)
        self._validate_can_add()
        attrs['role'] = USER_ROLE.REGIONAL_COORDINATOR
        return attrs

    class Meta:
        model = Portfolio
        fields = ['user', 'monitoring_sub_region']
        extra_kwargs = {
            'monitoring_sub_region': dict(required=True, allow_null=False),
        }


class AdminPortfolioSerializer(serializers.ModelSerializer):
    def _validate_unique(self, attrs) -> None:
        if Portfolio.objects.filter(
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
        attrs['role'] = USER_ROLE.ADMIN
        return attrs

    class Meta:
        model = Portfolio
        fields = ['user']


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
