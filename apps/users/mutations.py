from django.contrib.auth import login, logout
from django.utils.translation import gettext
from django.conf import settings
import graphene

from apps.users.schema import UserType
from apps.users.models import User
from apps.users.serializers import (
    LoginSerializer,
    RegisterSerializer,
    ActivateSerializer,
    UserSerializer,
    UserPasswordSerializer,
    ForgotPasswordSerializer,
    ReSetPasswordSerializer,
)
from utils.permissions import is_authenticated
from utils.error_types import CustomErrorType, mutation_is_not_valid
from utils.mutation import generate_input_type_for_serializer
from utils.validations import MissingCaptchaException
from .tasks import send_email
from django.utils.encoding import force_bytes, force_text
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils import timezone
from datetime import datetime, timedelta
from django.utils.dateparse import parse_datetime
from django.db import transaction

RegisterInputType = generate_input_type_for_serializer(
    'RegisterInputType',
    RegisterSerializer
)


class Register(graphene.Mutation):
    class Arguments:
        data = RegisterInputType(required=True)

    errors = graphene.List(graphene.NonNull(CustomErrorType))
    ok = graphene.Boolean()
    result = graphene.Field(UserType)
    captcha_required = graphene.Boolean(required=True, default_value=True)

    @staticmethod
    def mutate(root, info, data):
        serializer = RegisterSerializer(data=data,
                                        context={'request': info.context.request})
        if errors := mutation_is_not_valid(serializer):
            return Register(errors=errors, ok=False)
        instance = serializer.save()
        return Register(
            result=instance,
            errors=None,
            ok=True
        )


LoginInputType = generate_input_type_for_serializer(
    'LoginInputType',
    LoginSerializer
)


class Login(graphene.Mutation):
    class Arguments:
        data = LoginInputType(required=True)

    result = graphene.Field(UserType)
    errors = graphene.List(graphene.NonNull(CustomErrorType))
    ok = graphene.Boolean(required=True)
    captcha_required = graphene.Boolean(required=True, default_value=False)

    @staticmethod
    def mutate(root, info, data):
        serializer = LoginSerializer(data=data,
                                     context={'request': info.context.request})
        try:
            errors = mutation_is_not_valid(serializer)
        except MissingCaptchaException:
            return Login(ok=False, captcha_required=True)
        if errors:
            attempts = User._get_login_attempt(data['email'])
            return Login(
                errors=errors,
                ok=False,
                captcha_required=attempts >= settings.MAX_LOGIN_ATTEMPTS
            )
        if user := serializer.validated_data.get('user'):
            login(info.context.request, user)
        return Login(
            result=user,
            errors=None,
            ok=True
        )


ActivateInputType = generate_input_type_for_serializer(
    'ActivateInputType',
    ActivateSerializer
)


class Activate(graphene.Mutation):
    class Arguments:
        data = ActivateInputType(required=True)

    errors = graphene.List(graphene.NonNull(CustomErrorType))
    ok = graphene.Boolean()

    @staticmethod
    def mutate(root, info, data):
        serializer = ActivateSerializer(data=data,
                                        context={'request': info.context.request})
        if errors := mutation_is_not_valid(serializer):
            return Activate(errors=errors, ok=False)
        return Activate(errors=None, ok=True)


class Logout(graphene.Mutation):
    ok = graphene.Boolean()

    def mutate(self, info, *args, **kwargs):
        if info.context.user.is_authenticated:
            logout(info.context.request)
        return Logout(ok=True)


UserPasswordInputType = generate_input_type_for_serializer(
    'UserPasswordInputType',
    UserPasswordSerializer
)


class ChangeUserPassword(graphene.Mutation):
    class Arguments:
        data = UserPasswordInputType(required=True)

    errors = graphene.List(graphene.NonNull(CustomErrorType))
    ok = graphene.Boolean()
    result = graphene.Field(UserType)

    @staticmethod
    @is_authenticated()
    def mutate(root, info, data):
        serializer = UserPasswordSerializer(instance=info.context.user,
                                            data=data,
                                            context={'request': info.context.request},
                                            partial=True)
        if errors := mutation_is_not_valid(serializer):
            return ChangeUserPassword(errors=errors, ok=False)
        serializer.save()
        return ChangeUserPassword(result=info.context.user, errors=None, ok=True)


UserUpdateInputType = generate_input_type_for_serializer(
    'UserUpdateInputType',
    UserSerializer
)


class UpdateUser(graphene.Mutation):
    class Arguments:
        data = UserUpdateInputType(required=True)

    errors = graphene.List(graphene.NonNull(CustomErrorType))
    ok = graphene.Boolean()
    result = graphene.Field(UserType)

    @staticmethod
    @is_authenticated()
    def mutate(root, info, data):
        try:
            user = User.objects.get(id=data['id'])
        except User.DoesNotExist:
            return UpdateUser(
                errors=[
                    dict(field='nonFieldErrors', messages=gettext('User not found.'))
                ]
            )
        serializer = UserSerializer(instance=user,
                                    data=data,
                                    context={'request': info.context.request},
                                    partial=True)
        if errors := mutation_is_not_valid(serializer):
            return UpdateUser(errors=errors, ok=False)
        serializer.save()
        return UpdateUser(result=user, errors=None, ok=True)


ForgetPasswordType = generate_input_type_for_serializer(
    'ForgetPasswordType',
    ForgotPasswordSerializer
)


class ForgetPassword(graphene.Mutation):
    class Arguments:
        data = ForgetPasswordType(required=True)

    errors = graphene.List(graphene.NonNull(CustomErrorType))
    ok = graphene.Boolean()

    @staticmethod
    def mutate(root, info, data):
        serializer = ForgotPasswordSerializer(data=data)
        if errors := mutation_is_not_valid(serializer):
            return ForgetPassword(errors=errors, ok=False)
        email = serializer.validated_data.get("email")
        # if user exists for this email
        try:
            user = User.objects.get(email=email)
            # generate a password reset token with user's id and token created date
            code = urlsafe_base64_encode(force_bytes(f"{user.pk},{timezone.now() + timedelta(hours=24)}"))
            base_url = settings.FRONTEND_BASE_URL
            # Get base url by profile type
            button_url = f"{base_url}/reset-password/?password_reset_token={code}"
            message = (
                "We received a request to reset your Helix account password. "
                "If you wish to do so, please click below. Otherwise, you may "
                "safely disregard this email."
            )
        # if no user exists for this email
        except User.DoesNotExist:
            # explanatory email message
            return ForgetPassword(
                errors=[
                    dict(field='nonFieldErrors', messages=gettext(f'User with this email {email} does not exists.'))
                ]
            )
        subject = "Reset password request for Helix"
        context = {
            "heading": "Reset Password",
            "message": message,
            "button_text": "Reset Password",
        }
        if button_url:
            context["button_url"] = button_url
        transaction.on_commit(lambda: send_email(
                subject, message, [email], html_context=context
        ))
        return ForgetPassword(errors=None, ok=True)


ResetPasswordType = generate_input_type_for_serializer(
    'ResetPasswordType',
    ReSetPasswordSerializer
)


class ResetPassword(graphene.Mutation):
    class Arguments:
        data = ResetPasswordType(required=True)

    errors = graphene.List(graphene.NonNull(CustomErrorType))
    ok = graphene.Boolean()

    @staticmethod
    def mutate(root, info, data):
        serializer = ReSetPasswordSerializer(data=data)
        if errors := mutation_is_not_valid(serializer):
            return ResetPassword(errors=errors, ok=False)
        password_reset_token = serializer.validated_data.get("password_reset_token")
        user_id, token_created_time = None, None
        # Decode token and parse token created time
        try:
            decoded_data = force_text(urlsafe_base64_decode(password_reset_token)).split(',')
            user_id, token_created_time = decoded_data[0], parse_datetime(decoded_data[1])
        except (TypeError, ValueError, IndexError):
            return ResetPassword(
                errors=[
                    dict(field='nonFieldErrors', messages=gettext('Token is not correct, might be expired (24 hours).'))
                ]
            )
        if user_id and token_created_time:
            # Check if token expired
            if timezone.now() < token_created_time:
                # Check if user exists
                user = User.objects.filter(id=user_id)
                if not user.exists():
                    return ResetPassword(
                        errors=[
                            dict(field='nonFieldErrors', messages=gettext('Token is not correct, might be expired (24 hours).'))
                        ]
                    )
                # Get user object
                user = user.first()
                # check new password and confirmation match
                new_password = serializer.validated_data.get("new_password")
                new_password_confirmation = serializer.validated_data.get(
                    "new_password_confirmation"
                )
                if not new_password == new_password_confirmation:
                    return ResetPassword(
                        errors=[
                            dict(field='nonFieldErrors', messages=gettext('New password and confirmation not matching.'))
                        ]
                    )
                # Activate user (in case user just registered, not activated and forgets his/her password)
                user.is_active = True
                # set_password also hashes the password that the user will get
                user.set_password(serializer.validated_data.get("new_password"))
                user.save()
        return ResetPassword(errors=None, ok=True)


class Mutation(object):
    login = Login.Field()
    register = Register.Field()
    activate = Activate.Field()
    logout = Logout.Field()
    update_user = UpdateUser.Field()
    change_password = ChangeUserPassword.Field()
    forget_password = ForgetPassword.Field()
    rest_password = ResetPassword.Field()
