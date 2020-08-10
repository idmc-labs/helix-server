from django.contrib.auth import get_user_model, login
from graphene_django.rest_framework.mutation import SerializerMutation

from apps.users.serializers import LoginSerializer, RegisterSerializer, ActivateSerializer


class RegisterMutation(SerializerMutation):
    class Meta:
        serializer_class = RegisterSerializer


class LoginMutation(SerializerMutation):
    class Meta:
        serializer_class = LoginSerializer

    @classmethod
    def perform_mutate(cls, serializer, info):
        if user := serializer.validated_data.get('user', None):
            login(info.context, user)
        return super().perform_mutate(serializer, info)


class ActivateMutation(SerializerMutation):
    class Meta:
        serializer_class = ActivateSerializer


class Mutation(object):
    login = LoginMutation.Field()
    register = RegisterMutation.Field()
    activate = ActivateMutation.Field()
