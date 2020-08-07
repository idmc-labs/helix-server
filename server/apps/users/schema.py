from django.contrib.auth import get_user_model
from graphene import relay, ObjectType, Field
from graphene_django import DjangoObjectType

User = get_user_model()


class UserType(DjangoObjectType):
    class Meta:
        model = User


class Viewer(ObjectType):
    user = Field(UserType)

    def resolve_user(self, info, **kwargs):
        if info.context.user.is_authenticated:
            return info.context.user
        return None


class Query(object):
    viewer = Field(Viewer)

    def resolve_viewer(self, info, **kwargs):
        if info.context.user.is_authenticated:
            return info.context.user
        return None
