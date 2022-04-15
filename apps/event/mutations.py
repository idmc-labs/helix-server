import graphene
from graphene_django.filter.utils import get_filtering_args_from_filterset
from django.utils.translation import gettext

from apps.contrib.serializers import ExcelDownloadSerializer
from apps.event.models import Event, Actor, ContextOfViolence
from apps.event.filters import ActorFilter, EventFilter
from apps.event.schema import EventType, ActorType, ContextOfViolenceType
from apps.event.serializers import (
    EventSerializer,
    EventUpdateSerializer,
    ActorSerializer,
    ActorUpdateSerializer,
    CloneEventSerializer,
    ContextOfViolenceSerializer,
    ContextOfViolenceUpdateSerializer
)
from utils.error_types import CustomErrorType, mutation_is_not_valid
from utils.permissions import permission_checker
from utils.mutation import generate_input_type_for_serializer
from utils.common import convert_date_object_to_string_in_dict


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


class ExportEvents(graphene.Mutation):
    class Meta:
        arguments = get_filtering_args_from_filterset(
            EventFilter,
            EventType
        )

    errors = graphene.List(graphene.NonNull(CustomErrorType))
    ok = graphene.Boolean()

    @staticmethod
    def mutate(root, info, **kwargs):
        from apps.contrib.models import ExcelDownload

        serializer = ExcelDownloadSerializer(
            data=dict(
                download_type=int(ExcelDownload.DOWNLOAD_TYPES.EVENT),
                filters=convert_date_object_to_string_in_dict(kwargs),
            ),
            context=dict(request=info.context.request)
        )
        if errors := mutation_is_not_valid(serializer):
            return ExportEvents(errors=errors, ok=False)
        serializer.save()
        return ExportEvents(errors=None, ok=True)


class ExportActors(graphene.Mutation):
    class Meta:
        arguments = get_filtering_args_from_filterset(
            ActorFilter,
            ActorType
        )

    errors = graphene.List(graphene.NonNull(CustomErrorType))
    ok = graphene.Boolean()

    @staticmethod
    def mutate(root, info, **kwargs):
        from apps.contrib.models import ExcelDownload

        serializer = ExcelDownloadSerializer(
            data=dict(
                download_type=int(ExcelDownload.DOWNLOAD_TYPES.ACTOR),
                filters=convert_date_object_to_string_in_dict(kwargs),
            ),
            context=dict(request=info.context.request)
        )
        if errors := mutation_is_not_valid(serializer):
            return ExportActors(errors=errors, ok=False)
        serializer.save()
        return ExportActors(errors=None, ok=True)


CloneEntryInputType = generate_input_type_for_serializer(
    'CloneEventInputType',
    CloneEventSerializer
)


class CloneEvent(graphene.Mutation):
    class Arguments:
        data = CloneEntryInputType(required=True)

    errors = graphene.List(graphene.NonNull(CustomErrorType))
    ok = graphene.Boolean()
    result = graphene.Field(EventType)

    @staticmethod
    @permission_checker(['event.add_event'])
    def mutate(root, info, data):
        serializer = CloneEventSerializer(
            data=data,
            context=dict(request=info.context.request),
        )
        if errors := mutation_is_not_valid(serializer):
            return CloneEvent(errors=errors, ok=False)
        cloned_entries = serializer.save()
        return CloneEvent(result=cloned_entries, errors=None, ok=True)


ContextOfViolenceCreateInputType = generate_input_type_for_serializer(
    'ContextOfViolenceCreateInputType',
    ContextOfViolenceSerializer
)

ContextOfViolenceUpdateInputType = generate_input_type_for_serializer(
    'ContextOfViolenceUpdateInputType',
    ContextOfViolenceUpdateSerializer
)


class CreateContextOfViolence(graphene.Mutation):
    class Arguments:
        data = ContextOfViolenceCreateInputType(required=True)

    errors = graphene.List(graphene.NonNull(CustomErrorType))
    ok = graphene.Boolean()
    result = graphene.Field(ContextOfViolenceType)

    @staticmethod
    @permission_checker(['contextofviolence.add_contextofviolence'])
    def mutate(root, info, data):
        serializer = ContextOfViolenceSerializer(data=data, context=dict(request=info.context.request))
        if errors := mutation_is_not_valid(serializer):
            return CreateContextOfViolence(errors=errors, ok=False)
        instance = serializer.save()
        return CreateContextOfViolence(result=instance, errors=None, ok=True)


class UpdateContextOfViolence(graphene.Mutation):
    class Arguments:
        data = ContextOfViolenceUpdateInputType(required=True)

    errors = graphene.List(graphene.NonNull(CustomErrorType))
    ok = graphene.Boolean()
    result = graphene.Field(ContextOfViolenceType)

    @staticmethod
    @permission_checker(['contextofviolence.update_contextofviolence'])
    def mutate(root, info, data):
        try:
            instance = ContextOfViolence.objects.get(id=data['id'])
        except ContextOfViolence.DoesNotExist:
            return UpdateContextOfViolence(errors=[
                dict(field='nonFieldErrors', messages=gettext('Context of violence does not exist.'))
            ])
        serializer = ContextOfViolenceUpdateSerializer(
            instance=instance, data=data,
            context=dict(request=info.context.request), partial=True
        )
        if errors := mutation_is_not_valid(serializer):
            return UpdateContextOfViolence(errors=errors, ok=False)
        instance = serializer.save()
        return UpdateContextOfViolence(result=instance, errors=None, ok=True)


class DeleteContextOfViolence(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    errors = graphene.List(graphene.NonNull(CustomErrorType))
    ok = graphene.Boolean()
    result = graphene.Field(ContextOfViolenceType)

    @staticmethod
    @permission_checker(['contextofviolence.delete_contextofviolence'])
    def mutate(root, info, id):
        try:
            instance = ContextOfViolence.objects.get(id=id)
        except ContextOfViolence.DoesNotExist:
            return DeleteContextOfViolence(errors=[
                dict(field='nonFieldErrors', messages=gettext('Context of violence does not exist.'))
            ])
        instance.delete()
        instance.id = id
        return DeleteContextOfViolence(result=instance, errors=None, ok=True)


class Mutation(object):
    create_event = CreateEvent.Field()
    update_event = UpdateEvent.Field()
    delete_event = DeleteEvent.Field()
    create_actor = CreateActor.Field()
    update_actor = UpdateActor.Field()
    delete_actor = DeleteActor.Field()
    create_context_of_violence = CreateContextOfViolence.Field()
    update_context_of_violence = UpdateContextOfViolence.Field()
    delete_context_of_violence = DeleteContextOfViolence.Field()

    # exports
    export_events = ExportEvents.Field()
    export_actors = ExportActors.Field()
    clone_event = CloneEvent.Field()
