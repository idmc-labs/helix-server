import graphene
from django.utils.translation import gettext

from apps.event.models import Event, Actor
from apps.event.schema import EventType, ActorType
from apps.event.serializers import (
    EventSerializer,
    EventUpdateSerializer,
    ActorSerializer,
    ActorUpdateSerializer
)
from utils.error_types import CustomErrorType, mutation_is_not_valid
from utils.permissions import permission_checker
from utils.mutation import generate_input_type_for_serializer


ActorCreateInputType = generate_input_type_for_serializer(
    'ActorCreateInputType',
    ActorSerializer
)


ActorUpdateInputType = generate_input_type_for_serializer(
    'ActorUpdateInputType',
    ActorUpdateSerializer
)


class CreateActor(graphene.Mutation):
    class Arguments:
        data = ActorCreateInputType(required=True)

    errors = graphene.List(graphene.NonNull(CustomErrorType))
    ok = graphene.Boolean()
    result = graphene.Field(ActorType)

    @staticmethod
    @permission_checker(['event.add_actor'])
    def mutate(root, info, data):
        serializer = ActorSerializer(data=data, context={'request': info.context.request})
        if errors := mutation_is_not_valid(serializer):
            return CreateActor(errors=errors, ok=False)
        instance = serializer.save()
        return CreateActor(result=instance, errors=None, ok=True)


class UpdateActor(graphene.Mutation):
    class Arguments:
        data = ActorUpdateInputType(required=True)

    errors = graphene.List(graphene.NonNull(CustomErrorType))
    ok = graphene.Boolean()
    result = graphene.Field(ActorType)

    @staticmethod
    @permission_checker(['event.change_actor'])
    def mutate(root, info, data):
        try:
            instance = Actor.objects.get(id=data['id'])
        except Actor.DoesNotExist:
            return UpdateActor(errors=[
                dict(field='nonFieldErrors', messages=gettext('Actor does not exist.'))
            ])
        serializer = ActorSerializer(instance=instance, data=data,
                                     context=dict(request=info.context.request), partial=True)
        if errors := mutation_is_not_valid(serializer):
            return UpdateActor(errors=errors, ok=False)
        instance = serializer.save()
        return UpdateActor(result=instance, errors=None, ok=True)


class DeleteActor(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    errors = graphene.List(graphene.NonNull(CustomErrorType))
    ok = graphene.Boolean()
    result = graphene.Field(ActorType)

    @staticmethod
    @permission_checker(['event.delete_actor'])
    def mutate(root, info, id):
        try:
            instance = Actor.objects.get(id=id)
        except Actor.DoesNotExist:
            return DeleteActor(errors=[
                dict(field='nonFieldErrors', messages=gettext('Actor does not exist.'))
            ])
        instance.delete()
        instance.id = id
        return DeleteActor(result=instance, errors=None, ok=True)


EventCreateInputType = generate_input_type_for_serializer(
    'EventCreateInputType',
    EventSerializer
)


EventUpdateInputType = generate_input_type_for_serializer(
    'EventUpdateInputType',
    EventUpdateSerializer
)


class CreateEvent(graphene.Mutation):
    class Arguments:
        data = EventCreateInputType(required=True)

    errors = graphene.List(graphene.NonNull(CustomErrorType))
    ok = graphene.Boolean()
    result = graphene.Field(EventType)

    @staticmethod
    @permission_checker(['event.add_event'])
    def mutate(root, info, data):
        serializer = EventSerializer(data=data, context=dict(request=info.context.request))
        if errors := mutation_is_not_valid(serializer):
            return CreateEvent(errors=errors, ok=False)
        instance = serializer.save()
        return CreateEvent(result=instance, errors=None, ok=True)


class UpdateEvent(graphene.Mutation):
    class Arguments:
        data = EventUpdateInputType(required=True)

    errors = graphene.List(graphene.NonNull(CustomErrorType))
    ok = graphene.Boolean()
    result = graphene.Field(EventType)

    @staticmethod
    @permission_checker(['event.change_event'])
    def mutate(root, info, data):
        try:
            instance = Event.objects.get(id=data['id'])
        except Event.DoesNotExist:
            return UpdateEvent(errors=[
                dict(field='nonFieldErrors', messages=gettext('Event does not exist.'))
            ])
        serializer = EventSerializer(instance=instance, data=data,
                                     context=dict(request=info.context.request), partial=True)
        if errors := mutation_is_not_valid(serializer):
            return UpdateEvent(errors=errors, ok=False)
        instance = serializer.save()
        return UpdateEvent(result=instance, errors=None, ok=True)


class DeleteEvent(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    errors = graphene.List(graphene.NonNull(CustomErrorType))
    ok = graphene.Boolean()
    result = graphene.Field(EventType)

    @staticmethod
    @permission_checker(['event.delete_event'])
    def mutate(root, info, id):
        try:
            instance = Event.objects.get(id=id)
        except Event.DoesNotExist:
            return DeleteEvent(errors=[
                dict(field='nonFieldErrors', messages=gettext('Event does not exist.'))
            ])
        instance.delete()
        instance.id = id
        return DeleteEvent(result=instance, errors=None, ok=True)


class Mutation(object):
    create_event = CreateEvent.Field()
    update_event = UpdateEvent.Field()
    delete_event = DeleteEvent.Field()
    create_actor = CreateActor.Field()
    update_actor = UpdateActor.Field()
    delete_actor = DeleteActor.Field()
