from django.contrib.auth import login, logout
from django.utils.translation import gettext
import graphene

from apps.users.schema import UserType
from apps.users.models import User
from apps.users.serializers import (
    LoginSerializer,
    RegisterSerializer,
    ActivateSerializer,
    UserSerializer,
    UserPasswordSerializer,
)
from utils.permissions import is_authenticated
from utils.error_types import CustomErrorType, mutation_is_not_valid
from utils.mutation import generate_input_type_for_serializer


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

    @staticmethod
    def mutate(root, info, data):
        serializer = RegisterSerializer(data=data,
                                        context={'request': info.context})
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
    ok = graphene.Boolean()

    @staticmethod
    def mutate(root, info, data):
        serializer = LoginSerializer(data=data,
                                     context={'request': info.context})
        if errors := mutation_is_not_valid(serializer):
            return Login(errors=errors, ok=False)
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
                                        context={'request': info.context})
        if errors := mutation_is_not_valid(serializer):
            return Activate(errors=errors, ok=False)
        return Activate(errors=None, ok=True)


class Logout(graphene.Mutation):
    ok = graphene.Boolean()

    def mutate(self, info, *args, **kwargs):
        if info.context.user.is_authenticated:
            logout(info.context)
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
                                            context={'request': info.context},
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
                                    context={'request': info.context},
                                    partial=True)
        if errors := mutation_is_not_valid(serializer):
            return UpdateUser(errors=errors, ok=False)
        serializer.save()
        return UpdateUser(result=user, errors=None, ok=True)


class Mutation(object):
    login = Login.Field()
    register = Register.Field()
    activate = Activate.Field()
    logout = Logout.Field()
    update_user = UpdateUser.Field()
    change_password = ChangeUserPassword.Field()
