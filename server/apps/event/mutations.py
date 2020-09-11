import graphene
from django.utils.translation import gettext, gettext_lazy as _

from apps.crisis.enums import CrisisTypeGrapheneEnum
from apps.event.models import Event
from apps.event.schema import EventType
from apps.event.serializers import EventSerializer
from utils.error_types import CustomErrorType, mutation_is_not_valid
from utils.permissions import permission_checker


class EventCreateInputType(graphene.InputObjectType):
    crisis = graphene.ID(required=True)
    name = graphene.String(required=True)
    event_type = graphene.NonNull(CrisisTypeGrapheneEnum)
    glide_number = graphene.String()
    trigger = graphene.ID()
    trigger_sub_type = graphene.ID()
    violence = graphene.ID()
    violence_sub_type = graphene.ID()
    actor = graphene.ID()
    disaster_category = graphene.ID()
    disaster_sub_category = graphene.ID()
    disaster_type = graphene.ID()
    disaster_sub_type = graphene.ID()
    countries = graphene.List(graphene.ID, required=False)
    start_date = graphene.Date()
    end_date = graphene.Date()
    event_narrative = graphene.String()


class EventUpdateInputType(graphene.InputObjectType):
    id = graphene.ID(required=True)
    crisis = graphene.ID()
    name = graphene.String()
    event_type = graphene.Field(CrisisTypeGrapheneEnum)
    glide_number = graphene.String()
    trigger = graphene.ID()
    trigger_sub_type = graphene.ID()
    violence = graphene.ID()
    violence_sub_type = graphene.ID()
    actor = graphene.ID()
    disaster_category = graphene.ID()
    disaster_sub_category = graphene.ID()
    disaster_type = graphene.ID()
    disaster_sub_type = graphene.ID()
    countries = graphene.List(graphene.ID)
    start_date = graphene.Date()
    end_date = graphene.Date()
    event_narrative = graphene.String()


class CreateEvent(graphene.Mutation):
    class Arguments:
        event = EventCreateInputType(required=True)

    errors = graphene.List(CustomErrorType)
    ok = graphene.Boolean()
    event = graphene.Field(EventType)

    @staticmethod
    @permission_checker(['event.add_event'])
    def mutate(root, info, event):
        serializer = EventSerializer(data=event)
        if errors := mutation_is_not_valid(serializer):
            return CreateEvent(errors=errors, ok=False)
        instance = serializer.save()
        return CreateEvent(event=instance, errors=None, ok=True)


class UpdateEvent(graphene.Mutation):
    class Arguments:
        event = EventUpdateInputType(required=True)

    errors = graphene.List(CustomErrorType)
    ok = graphene.Boolean()
    event = graphene.Field(EventType)

    @staticmethod
    @permission_checker(['event.change_event'])
    def mutate(root, info, event):
        try:
            instance = Event.objects.get(id=event['id'])
        except Event.DoesNotExist:
            return UpdateEvent(errors=[
                CustomErrorType(field='non_field_errors', messages=gettext('Event does not exist.'))
            ])
        serializer = EventSerializer(instance=instance, data=event, partial=True)
        if errors := mutation_is_not_valid(serializer):
            return UpdateEvent(errors=errors, ok=False)
        instance = serializer.save()
        return UpdateEvent(event=instance, errors=None, ok=True)


class DeleteEvent(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    errors = graphene.List(CustomErrorType)
    ok = graphene.Boolean()
    event = graphene.Field(EventType)

    @staticmethod
    @permission_checker(['event.delete_event'])
    def mutate(root, info, id):
        try:
            instance = Event.objects.get(id=id)
        except Event.DoesNotExist:
            return DeleteEvent(errors=[
                CustomErrorType(field='non_field_errors', messages=gettext('Event does not exist.'))
            ])
        instance.delete()
        instance.id = id
        return DeleteEvent(event=instance, errors=None, ok=True)


class Mutation(object):
    create_event = CreateEvent.Field()
    update_event = UpdateEvent.Field()
    delete_event = DeleteEvent.Field()
