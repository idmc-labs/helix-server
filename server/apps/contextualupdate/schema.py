import graphene
from graphene_django import DjangoObjectType
from graphene_django_extras import PageGraphqlPagination, DjangoObjectField

from apps.crisis.enums import CrisisTypeGrapheneEnum
from apps.contextualupdate.models import ContextualUpdate
from apps.contextualupdate.filters import ContextualUpdateFilter
from utils.fields import DjangoPaginatedListObjectField, CustomDjangoListObjectType


class ContextualUpdateType(DjangoObjectType):
    class Meta:
        model = ContextualUpdate

    crisis_type = graphene.Field(CrisisTypeGrapheneEnum)


class ContextualUpdateListType(CustomDjangoListObjectType):
    class Meta:
        model = ContextualUpdate
        filterset_class = ContextualUpdateFilter


class Query:
    contextual_update = DjangoObjectField(ContextualUpdateType)
    contextual_update_list = DjangoPaginatedListObjectField(ContextualUpdateListType,
                                                            pagination=PageGraphqlPagination(
                                                                page_size_query_param='pageSize'
                                                            ))
