from django.contrib.auth import get_user_model
import graphene
from graphene import Field, ObjectType
from graphene.types.utils import get_type
from graphene_django import DjangoObjectType
from graphene_django_extras import PageGraphqlPagination, DjangoObjectType as ExtraDOT

from utils.fields import DjangoPaginatedListObjectField, CustomDjangoListObjectType
from apps.users.filters import UserFilter

User = get_user_model()

EntryListType = get_type('apps.entry.schema.EntryListType')


class PermissionsType(ObjectType):
    action = graphene.String()
    entities = graphene.List(graphene.String)


class UserType(DjangoObjectType):
    class Meta:
        model = User
        exclude_fields = ('password',)

    review_entries = DjangoPaginatedListObjectField(EntryListType,
                                                   pagination=PageGraphqlPagination(
                                                        page_size_query_param='pageSize'
                                                    ), accessor='review_entries')
    created_entry = DjangoPaginatedListObjectField(EntryListType,
                                                   pagination=PageGraphqlPagination(
                                                       page_size_query_param='pageSize'
                                                   ), accessor='created_entry')
    role = Field(graphene.String)
    permissions = graphene.List(PermissionsType)
    full_name = Field(graphene.String)


class UserListType(CustomDjangoListObjectType):
    class Meta:
        model = User
        filterset_class = UserFilter


class Query(object):
    me = Field(UserType)
    users = DjangoPaginatedListObjectField(UserListType)

    def resolve_me(self, info, **kwargs):
        if info.context.user.is_authenticated:
            return info.context.user
        return None
