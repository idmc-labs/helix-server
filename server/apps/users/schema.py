from django.contrib.auth import get_user_model
from graphene import Field
from graphene_django import DjangoObjectType

User = get_user_model()


class UserType(DjangoObjectType):
    class Meta:
        model = User
        exclude = ('password',)


class Query(object):
    me = Field(UserType)

    def resolve_me(self, info, **kwargs):
        if info.context.user.is_authenticated:
            return info.context.user
        return None
