import graphene
from graphene.types.utils import get_type
from graphene_django import DjangoObjectType
from graphene_django_extras import DjangoObjectField

from apps.crisis.enums import CrisisTypeGrapheneEnum
from apps.contextualupdate.models import ContextualUpdate
from apps.contextualupdate.filters import ContextualUpdateFilter
from utils.graphene.types import CustomDjangoListObjectType
from utils.graphene.fields import DjangoPaginatedListObjectField
from utils.pagination import PageGraphqlPaginationWithoutCount


class ContextualUpdateType(DjangoObjectType):
    class Meta:
        model = ContextualUpdate

    crisis_types = graphene.List(graphene.NonNull(CrisisTypeGrapheneEnum))
    sources = graphene.Dynamic(
        lambda: DjangoPaginatedListObjectField(
            get_type('apps.organization.schema.OrganizationListType'),
            related_name='sources',
            reverse_related_name='sourced_contextual_updates',
        ))
    publishers = graphene.Dynamic(
        lambda: DjangoPaginatedListObjectField(
            get_type('apps.organization.schema.OrganizationListType'),
            related_name='publishers',
            reverse_related_name='published_contextual_updates',
        ))


class ContextualUpdateListType(CustomDjangoListObjectType):
    class Meta:
        model = ContextualUpdate
        filterset_class = ContextualUpdateFilter


class Query:
    contextual_update = DjangoObjectField(ContextualUpdateType)
    contextual_update_list = DjangoPaginatedListObjectField(ContextualUpdateListType,
                                                            pagination=PageGraphqlPaginationWithoutCount(
                                                                page_size_query_param='pageSize'
                                                            ))
