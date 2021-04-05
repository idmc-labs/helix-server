from django.contrib.auth import get_user_model
import graphene
from graphene import Field, ObjectType
from graphene.types.utils import get_type
from graphene_django import DjangoObjectType
from graphene_django_extras import DjangoObjectField

from utils.graphene.types import CustomDjangoListObjectType
from utils.graphene.fields import DjangoPaginatedListObjectField
from utils.pagination import PageGraphqlPaginationWithoutCount
from apps.users.filters import UserFilter, ReviewerUserFilter

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

    reviewing = DjangoPaginatedListObjectField(
        EntryReviewerListType,
        pagination=PageGraphqlPaginationWithoutCount(
            page_size_query_param='pageSize'
        ),
        related_name='reviewing',
        reverse_related_name='reviewer',
    )
    created_entry = DjangoPaginatedListObjectField(
        EntryListType,
        pagination=PageGraphqlPaginationWithoutCount(
            page_size_query_param='pageSize'
        ),
        related_name='created_entry',
        reverse_related_name='created_by',
    )
    role = Field(PermissionRoleEnum)
    permissions = graphene.List(graphene.NonNull(PermissionsType))
    full_name = Field(graphene.String, required=True)


class UserListType(CustomDjangoListObjectType):
    class Meta:
        model = User
        filterset_class = UserFilter


class Query(object):
    me = Field(UserType)
    user = DjangoObjectField(UserType)
    users = DjangoPaginatedListObjectField(UserListType,
                                           pagination=PageGraphqlPaginationWithoutCount(
                                               page_size_query_param='pageSize'
                                           ))
    reviewer_user_list = DjangoPaginatedListObjectField(UserListType,
                                                        pagination=PageGraphqlPaginationWithoutCount(
                                                            page_size_query_param='pageSize'
                                                        ), filterset_class=ReviewerUserFilter)

    def resolve_me(self, info, **kwargs):
        if info.context.user.is_authenticated:
            return info.context.user
        return None
