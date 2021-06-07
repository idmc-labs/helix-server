from typing import Union

from django.contrib.auth import get_user_model
from django.db.models import Model
import graphene
from graphene import Field, ObjectType
from graphene.types.utils import get_type
from graphene_django import DjangoObjectType
from graphene_django_extras import DjangoObjectField

from utils.graphene.types import CustomDjangoListObjectType
from utils.graphene.fields import DjangoPaginatedListObjectField
from utils.pagination import PageGraphqlPaginationWithoutCount
from apps.users.filters import UserFilter, ReviewerUserFilter
from apps.users.roles import USER_ROLE
from apps.users.models import Portfolio

from .enums import PermissionActionEnum, PermissionModelEnum, PermissionRoleEnum

User: Model = get_user_model()

EntryListType: ObjectType = get_type('apps.entry.schema.EntryListType')
EntryReviewerListType: CustomDjangoListObjectType = get_type('apps.entry.schema.EntryReviewerListType')


class PermissionsType(ObjectType):
    action = Field(PermissionActionEnum, required=True)
    entities = graphene.List(graphene.NonNull(PermissionModelEnum), required=True)


class PortfolioType(DjangoObjectType):
    class Meta:
        model = Portfolio

    role = Field(PermissionRoleEnum)
    permissions = graphene.List(graphene.NonNull(PermissionsType))


class UserType(DjangoObjectType):
    class Meta:
        model = User
        fields = ('created_entry', 'date_joined', 'email', 'first_name', 'last_name',
                  'full_name', 'id', 'is_active', 'last_login',
                  'reviewing', 'role', 'username')

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
    full_name = Field(graphene.String, required=True)
    email = graphene.String()
    portfolios = graphene.List(PortfolioType)

    @staticmethod
    def resolve_role(root, info, **kwargs):
        if info.context.request.user == root:
            return root.role
        if info.context.request.user.role in [USER_ROLE.ADMIN]:
            return root.role

    @staticmethod
    def resolve_email(root, info, **kwargs):
        if root == info.context.request.user:
            return root.email


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

    @staticmethod
    def resolve_me(root, info, **kwargs) -> Union[User, None]:
        if info.context.user.is_authenticated:
            return info.context.user
        return None
