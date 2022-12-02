from typing import Union

from django.contrib.auth import get_user_model
from django.db.models import Model
import graphene
from graphene import Field, ObjectType
from graphene.types.generic import GenericScalar
from graphene.types.utils import get_type
from graphene_django import DjangoObjectType
from graphene_django_extras import DjangoObjectField
from utils.graphene.enums import EnumDescription

from utils.graphene.types import CustomDjangoListObjectType
from utils.graphene.fields import DjangoPaginatedListObjectField
from utils.graphene.pagination import PageGraphqlPaginationWithoutCount
from apps.users.filters import UserFilter, PortfolioFilter
from apps.users.roles import USER_ROLE
from apps.users.models import Portfolio

from .enums import PermissionActionEnum, PermissionModelEnum, PermissionRoleEnum

User: Model = get_user_model()

EntryListType: ObjectType = get_type('apps.entry.schema.EntryListType')


class PermissionsType(ObjectType):
    action = Field(PermissionActionEnum, required=True)
    action_display = EnumDescription(source='get_action_display')
    entities = graphene.List(graphene.NonNull(PermissionModelEnum), required=True)


class PortfolioType(DjangoObjectType):
    class Meta:
        model = Portfolio

    role = Field(PermissionRoleEnum, required=True)
    role_display = EnumDescription(source='get_role_display')
    permissions = graphene.List(graphene.NonNull(PermissionsType))


class PortfolioListType(CustomDjangoListObjectType):
    class Meta:
        model = Portfolio
        filterset_class = PortfolioFilter


class UserType(DjangoObjectType):
    class Meta:
        model = User
        fields = (
            'created_entry', 'date_joined', 'email', 'first_name', 'last_name',
            'full_name', 'id', 'is_active', 'last_login', 'username'
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
    portfolios = graphene.List(graphene.NonNull(PortfolioType))
    portfolio_role = Field(PermissionRoleEnum)
    portfolio_role_display = graphene.String()
    permissions = graphene.List(graphene.NonNull(PermissionsType))
    is_admin = graphene.Boolean()

    @staticmethod
    def resolve_permissions(root, info, **kwargs):
        if root == info.context.request.user:
            return root.permissions

    @staticmethod
    def resolve_email(root, info, **kwargs):
        if root == info.context.request.user:
            return root.email

    @staticmethod
    def resolve_is_admin(root, info, **kwargs):
        if root.highest_role == USER_ROLE.ADMIN.value:
            return True
        return False

    @staticmethod
    def resolve_portfolio_role(root, info, **kwargs):
        return root.portfolio_role

    @staticmethod
    def resolve_portfolios(root, info, **kwargs):
        return Portfolio.objects.filter(user=root.id)

    def resolve_portfolio_role_display(root, info, **kwargs):
        return info.context.user_portfolio_role_loader.load(root.id)


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
    portfolios = DjangoPaginatedListObjectField(PortfolioListType,
                                                pagination=PageGraphqlPaginationWithoutCount(
                                                    page_size_query_param='pageSize'
                                                ))
    role_with_region_allowed_map = Field(GenericScalar)

    @staticmethod
    def resolve_role_with_region_allowed_map(root, info, **kwargs):
        return Portfolio.get_role_allows_region_map()

    @staticmethod
    def resolve_me(root, info, **kwargs) -> Union[User, None]:
        if info.context.user.is_authenticated:
            return info.context.user
        return None
