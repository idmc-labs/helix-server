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


class UserPortfolioMetaDataType(graphene.ObjectType):
    is_admin = graphene.Boolean()
    is_directors_office = graphene.Boolean()
    is_reporting_team = graphene.Boolean()
    portfolio_role = Field(PermissionRoleEnum)
    portfolio_role_display = graphene.String()


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
    portfolios_metadata = graphene.Field(UserPortfolioMetaDataType, required=True)
    permissions = graphene.List(graphene.NonNull(PermissionsType))

    @staticmethod
    def resolve_permissions(root, info, **_):
        if root == info.context.request.user:
            return root.permissions

    @staticmethod
    def resolve_email(root, info, **_):
        if root == info.context.request.user:
            return root.email

    @staticmethod
    def resolve_portfolios_metadata(user, info, **_):
        return info.context.user_portfolios_metadata.load(user.id)

    @staticmethod
    def resolve_portfolios(root, info, **_):
        return Portfolio.objects.filter(user=root.id).select_related('monitoring_sub_region')


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
