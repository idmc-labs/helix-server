from django.contrib.auth import login, logout
import graphene
from graphene_django.rest_framework.mutation import SerializerMutation

from apps.users.schema import UserType
from apps.users.serializers import LoginSerializer, RegisterSerializer, ActivateSerializer
from utils.error_types import CustomErrorType, mutation_is_not_valid


class RegisterMutationInput(graphene.InputObjectType):
    email = graphene.String(required=True)
    first_name = graphene.String()
    last_name = graphene.String()
    password = graphene.String(required=True)
    username = graphene.String(required=True)


class RegisterMutation(graphene.Mutation):
    class Arguments:
        input = RegisterMutationInput(required=True)

    errors = graphene.List(CustomErrorType)
    ok = graphene.Boolean()
    first_name = graphene.String()
    last_name = graphene.String()
    email = graphene.String()
    username = graphene.String()

    @staticmethod
    def mutate(root, info, input):
        serializer = RegisterSerializer(data=input,
                                        context={'request': info.context})
        if errors := mutation_is_not_valid(serializer):
            return RegisterMutation(errors=errors, ok=False)
        instance = serializer.save()
        return RegisterMutation(
            first_name=instance.first_name, 
            last_name=instance.last_name, 
            email=instance.email, 
            username=instance.username, 
            errors=None, 
            ok=True
        )


class LoginMutationInput(graphene.InputObjectType):
    email = graphene.String(required=True)
    password = graphene.String(required=True)


class LoginMutation(graphene.Mutation):
    class Arguments:
        input = LoginMutationInput(required=True)

    me = graphene.Field(UserType)
    errors = graphene.List(CustomErrorType)
    ok = graphene.Boolean()

    @staticmethod
    def mutate(root, info, input):
        serializer = LoginSerializer(data=input,
                                     context={'request': info.context})
        if errors := mutation_is_not_valid(serializer):
            return LoginMutation(errors=errors, ok=False)
        if user := serializer.validated_data.get('user'):
            login(info.context, user)
        return LoginMutation(
            me=user,
            errors=None,
            ok=True
        )


class ActivateMutationInput(graphene.InputObjectType):
    uid = graphene.String(required=True)
    token = graphene.String(required=True)


class ActivateMutation(graphene.Mutation):
    class Arguments:
        input = ActivateMutationInput(required=True)

    errors = graphene.List(CustomErrorType)
    ok = graphene.Boolean()

    @staticmethod
    def mutate(root, info, input):
        serializer = ActivateSerializer(data=input,
                                        context={'request': info.context})
        if errors := mutation_is_not_valid(serializer):
            return ActivateMutation(errors=errors, ok=False)
        return ActivateMutation(errors=None, ok=True)


class LogoutMutation(graphene.Mutation):
    ok = graphene.Boolean()

    def mutate(self, info, *args, **kwargs):
        if info.context.user.is_authenticated:
            logout(info.context)
        return LogoutMutation(ok=True)


class Mutation(object):
    login = LoginMutation.Field()
    register = RegisterMutation.Field()
    activate = ActivateMutation.Field()
    logout = LogoutMutation.Field()
