from django.contrib.auth import get_user_model
import graphene
from graphene import Field, ObjectType
from graphene.types.utils import get_type
from graphene_django import DjangoObjectType
from graphene_django_extras import PageGraphqlPagination, DjangoObjectType as ExtraDOT

from utils.fields import DjangoPaginatedListObjectField, CustomDjangoListObjectType
from apps.users.filters import UserFilter

from .enums import PermissionActionEnum, PermissionModelEnum, PermissionRoleEnum

User = get_user_model()

EntryListType = get_type('apps.entry.schema.EntryListType')
EntryReviewerListType = get_type('apps.entry.schema.EntryReviewerListType')


class PermissionsType(ObjectType):
    action = Field(PermissionActionEnum, required=True)
    entities = graphene.List(graphene.NonNull(PermissionModelEnum), required=True)


class UserType(DjangoObjectType):
    class Meta:
        model = User
        fields = ('created_entry', 'date_joined', 'email', 'first_name', 'last_name',
                  'full_name', 'id', 'is_active', 'last_login',
                  'permissions', 'reviewing', 'role', 'username')

    reviewing = DjangoPaginatedListObjectField(EntryReviewerListType,
                                               pagination=PageGraphqlPagination(
                                                   page_size_query_param='pageSize'
                                               ), accessor='reviewing')
    created_entry = DjangoPaginatedListObjectField(EntryListType,
                                                   pagination=PageGraphqlPagination(
                                                       page_size_query_param='pageSize'
                                                   ), accessor='created_entry')
    role = Field(PermissionRoleEnum)
    permissions = graphene.List(graphene.NonNull(PermissionsType))
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
