import graphene
from graphene_django import DjangoObjectType
from graphene_django_extras import PageGraphqlPagination, DjangoObjectField, DjangoFilterListField

from apps.country.schema import CountryType
from apps.crisis.enums import CrisisTypeGrapheneEnum
from apps.event.models import (
    Event,
    Trigger,
    TriggerSubType,
    Violence,
    ViolenceSubType,
    Actor,
    DisasterSubCategory,
    DisasterCategory,
    DisasterSubType,
    DisasterType
)
from apps.event.filters import EventFilter
from utils.fields import DjangoPaginatedListObjectField, CustomDjangoListObjectType, CustomDjangoListField


class TriggerSubObjectType(DjangoObjectType):
    class Meta:
        model = TriggerSubType
        exclude_fields = ('events', 'trigger')
        filter_fields = {}


class TriggerSubObjectListType(CustomDjangoListObjectType):
    class Meta:
        model = TriggerSubType
        filter_fields = {
            'name': ['icontains']
        }


class TriggerType(DjangoObjectType):
    class Meta:
        model = Trigger
        exclude_fields = ('events',)


class TriggerListType(CustomDjangoListObjectType):
    class Meta:
        model = Trigger
        filter_fields = {
            'name': ['icontains']
        }


class ViolenceSubObjectType(DjangoObjectType):
    class Meta:
        model = ViolenceSubType
        exclude_fields = ('events', 'violence')


class ViolenceSubObjectListType(CustomDjangoListObjectType):
    class Meta:
        model = ViolenceSubType
        filter_fields = {
            'id': ['iexact'],
        }


class ViolenceType(DjangoObjectType):
    class Meta:
        model = Violence
        exclude_fields = ('events',)

    sub_types = DjangoPaginatedListObjectField(ViolenceSubObjectListType)


class ViolenceListType(CustomDjangoListObjectType):
    class Meta:
        model = Violence
        filter_fields = {
            'id': ['iexact'],
        }


class ActorType(DjangoObjectType):
    class Meta:
        model = Actor
        exclude_fields = ('events',)


class ActorListType(CustomDjangoListObjectType):
    class Meta:
        model = Actor
        filter_fields = {
            'name': ['icontains']
        }


class DisasterSubObjectType(DjangoObjectType):
    class Meta:
        model = DisasterSubType
        exclude_fields = ('events', 'type')


class DisasterSubObjectListType(CustomDjangoListObjectType):
    class Meta:
        model = DisasterSubType
        filter_fields = {
            'name': ['icontains'],
        }


class DisasterTypeObjectType(DjangoObjectType):
    class Meta:
        model = DisasterType
        exclude_fields = ('events', 'disaster_sub_category')

    sub_types = DjangoPaginatedListObjectField(DisasterSubObjectListType)


class DisasterTypeObjectListType(CustomDjangoListObjectType):
    class Meta:
        model = DisasterType
        filter_fields = {
            'name': ['icontains'],
        }


class DisasterSubCategoryType(DjangoObjectType):
    class Meta:
        model = DisasterSubCategory
        exclude_fields = ('events', 'category')

    types = DjangoPaginatedListObjectField(DisasterTypeObjectListType)


class DisasterSubCategoryListType(CustomDjangoListObjectType):
    class Meta:
        model = DisasterSubCategory
        filter_fields = {
            'name': ['icontains'],
        }


class DisasterCategoryType(DjangoObjectType):
    class Meta:
        model = DisasterCategory
        exclude_fields = ('events',)

    sub_categories = DjangoPaginatedListObjectField(DisasterSubCategoryListType)


class DisasterCategoryListType(CustomDjangoListObjectType):
    class Meta:
        model = DisasterCategory
        filter_fields = {
            'name': ['icontains'],
        }


class EventType(DjangoObjectType):
    class Meta:
        model = Event
        exclude_fields = ('entries',)

    event_type = graphene.Field(CrisisTypeGrapheneEnum)
    trigger = graphene.Field(TriggerType)
    trigger_sub_type = graphene.Field(TriggerSubObjectType)
    violence = graphene.Field(ViolenceType)
    violence_sub_type = graphene.Field(ViolenceSubObjectType)
    actor = graphene.Field(ActorType)


class EventListType(CustomDjangoListObjectType):
    class Meta:
        model = Event
        filterset_class = EventFilter


class Query:
    trigger_list = DjangoPaginatedListObjectField(TriggerListType)
    sub_trigger_list = DjangoPaginatedListObjectField(TriggerSubObjectListType)
    violence_list = DjangoPaginatedListObjectField(ViolenceListType)
    actor = DjangoObjectField(ActorType)
    actor_list = DjangoPaginatedListObjectField(ActorListType,
                                                pagination=PageGraphqlPagination(
                                                    page_size_query_param='pageSize'
                                                ))
    disaster_category_list = DjangoPaginatedListObjectField(DisasterCategoryListType)
    disaster_sub_category_list = DjangoPaginatedListObjectField(DisasterSubCategoryListType)
    disaster_type_list = DjangoPaginatedListObjectField(DisasterTypeObjectListType)
    disaster_sub_type_list = DjangoPaginatedListObjectField(DisasterSubObjectListType)

    event = DjangoObjectField(EventType)
    event_list = DjangoPaginatedListObjectField(EventListType,
                                                pagination=PageGraphqlPagination(
                                                    page_size_query_param='pageSize'
                                                ))
