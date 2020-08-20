import graphene
from graphene_django_extras import DjangoObjectType, PageGraphqlPagination, DjangoObjectField, DjangoFilterListField

from apps.crisis.schema import CrisisType
from apps.event.models import Event, Trigger, TriggerSubType, Violence, ViolenceSubType, Actor, DisasterSubCategory, \
    DisasterCategory, DisasterSubType, DisasterType
from utils.fields import DjangoPaginatedListObjectField, CustomDjangoListObjectType, CustomDjangoListField


class TriggerSubObjectType(DjangoObjectType):
    class Meta:
        model = TriggerSubType
        exclude_fields = ('events', 'trigger')
        filter_fields = {
            'name': ['icontains']
        }


class TriggerType(DjangoObjectType):
    class Meta:
        model = Trigger
        exclude_fields = ('events',)
        filter_fields = {
            'id': ['exact'],
            'name': ['icontains']
        }

    sub_types = DjangoFilterListField(TriggerSubObjectType)


class ViolenceSubObjectType(DjangoObjectType):
    class Meta:
        model = ViolenceSubType
        exclude_fields = ('events', 'violence')
        filter_fields = {
            'violence': ['exact'],
            'name': ['icontains']
        }


class ViolenceType(DjangoObjectType):
    class Meta:
        model = Violence
        exclude_fields = ('events',)
        filter_fields = {
            'name': ['icontains']
        }

    sub_types = CustomDjangoListField(ViolenceSubObjectType)


class ActorType(DjangoObjectType):
    class Meta:
        model = Actor
        exclude_fields = ('events',)
        filter_fields = {
            'id': ['exact'],
            'name': ['icontains']
        }


class DisasterSubObjectType(DjangoObjectType):
    class Meta:
        model = DisasterSubType
        exclude_fields = ('events', 'type')
        filter_fields = {
            'name': ['icontains']
        }


class DisasterTypeObjectType(DjangoObjectType):
    class Meta:
        model = DisasterType
        exclude_fields = ('events', 'disaster_sub_category')
        filter_fields = {
            'id': ['exact'],
            'name': ['icontains']
        }

    sub_types = DjangoFilterListField(DisasterSubObjectType)


class DisasterSubCategoryType(DjangoObjectType):
    class Meta:
        model = DisasterSubCategory
        exclude_fields = ('events', 'category')
        filter_fields = {
            'name': ['icontains']
        }

    types = DjangoFilterListField(DisasterTypeObjectType)


class DisasterCategoryType(DjangoObjectType):
    class Meta:
        model = DisasterCategory
        exclude_fields = ('events',)
        filter_fields = {
            'id': ['exact'],
            'name': ['icontains']
        }

    sub_categories = DjangoFilterListField(DisasterSubCategoryType)


class EventType(DjangoObjectType):
    class Meta:
        model = Event

    crisis = graphene.Field(CrisisType)
    trigger = graphene.Field(TriggerType)
    trigger_sub_type = graphene.Field(TriggerSubObjectType)
    violence = graphene.Field(ViolenceType)
    violence_sub_type = graphene.Field(ViolenceSubObjectType)
    actor = graphene.Field(ActorType)


class EventListType(CustomDjangoListObjectType):
    class Meta:
        model = Event


class Query:
    trigger_list = DjangoFilterListField(TriggerType)
    violence_list = DjangoFilterListField(ViolenceType)
    actor_list = DjangoFilterListField(ActorType)
    disaster_category_list = DjangoFilterListField(DisasterCategoryType)
    disaster_sub_category_list = DjangoFilterListField(DisasterSubCategoryType)
    disaster_type_list = DjangoFilterListField(DisasterTypeObjectType)

    event = DjangoObjectField(EventType)
    event_list = DjangoPaginatedListObjectField(EventListType,
                                                pagination=PageGraphqlPagination(
                                                    page_size_query_param='pageSize'
                                                ))
