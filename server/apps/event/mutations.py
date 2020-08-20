import graphene

from apps.crisis.enums import CrisisTypeGrapheneEnum
from apps.event.models import Event
from apps.event.schema import EventType
from apps.event.serializers import EventSerializer
from utils.error_types import CustomErrorType, mutation_is_not_valid


class EventCreateInputType(graphene.InputObjectType):
    crisis = graphene.Int(required=True)
    name = graphene.String(required=True)
    event_type = graphene.NonNull(CrisisTypeGrapheneEnum)
    glide_number = graphene.String()
    trigger = graphene.Int()
    trigger_sub_type = graphene.Int()
    violence = graphene.Int()
    violence_sub_type = graphene.Int()
    actor = graphene.Int()
    disaster_category = graphene.Int()
    disaster_sub_category = graphene.Int()
    disaster_type = graphene.Int()
    disaster_sub_type = graphene.Int()
    countries = graphene.List(graphene.Int, required=False)
    start_date = graphene.Date()
    end_date = graphene.Date()
    event_narrative = graphene.String()


class EventUpdateInputType(graphene.InputObjectType):
    id = graphene.Int(required=True)
    crisis = graphene.Int()
    name = graphene.String()
    event_type = graphene.Field(CrisisTypeGrapheneEnum)
    glide_number = graphene.String()
    trigger = graphene.Int()
    trigger_sub_type = graphene.Int()
    violence = graphene.Int()
    violence_sub_type = graphene.Int()
    actor = graphene.Int()
    disaster_category = graphene.Int()
    disaster_sub_category = graphene.Int()
    disaster_type = graphene.Int()
    disaster_sub_type = graphene.Int()
    countries = graphene.List(graphene.Int)
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
    def mutate(root, info, event):
        try:
            instance = Event.objects.get(id=event['id'])
        except Event.DoesNotExist:
            return UpdateEvent(errors=[
                CustomErrorType(field='non_field_errors', messages=['Event Does Not Exist.'])
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
    def mutate(root, info, event):
        try:
            instance = Event.objects.get(id=event['id'])
        except Event.DoesNotExist:
            return DeleteEvent(errors=[
                CustomErrorType(field='non_field_errors', messages=['Event Does Not Exist.'])
            ])
        instance.delete()
        instance.id = event['id']
        return DeleteEvent(event=instance, errors=None, ok=True)


class Mutation(object):
    create_event = CreateEvent.Field()
    update_event = UpdateEvent.Field()
    delete_event = DeleteEvent.Field()
