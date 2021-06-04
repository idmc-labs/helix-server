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
