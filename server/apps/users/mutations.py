from django.contrib.auth import get_user_model, login, logout
import graphene
from graphene_django.rest_framework.mutation import SerializerMutation

from apps.users.schema import UserType
from apps.users.serializers import LoginSerializer, RegisterSerializer, ActivateSerializer


class RegisterMutation(SerializerMutation):
    class Meta:
        serializer_class = RegisterSerializer


class LoginMutation(SerializerMutation):
    class Meta:
        serializer_class = LoginSerializer

    me = graphene.Field(UserType)

    @classmethod
    def perform_mutate(cls, serializer, info):
        if user := serializer.validated_data.get('user', None):
            login(info.context, user)
        return cls(errors=None, me=user)


class ActivateMutation(SerializerMutation):
    class Meta:
        serializer_class = ActivateSerializer


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
