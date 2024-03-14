import graphene
from django.utils import timezone
from django.utils.translation import gettext

from utils.error_types import CustomErrorType, mutation_is_not_valid
from utils.permissions import permission_checker
from utils.mutation import generate_input_type_for_serializer
from apps.contrib.models import ExcelDownload
from apps.contrib.mutations import ExportBaseMutation
from apps.event.models import Event, Actor, ContextOfViolence
from apps.event.filters import (
    ActorFilterDataInputType,
    EventFilterDataInputType,
    ContextOfViolenceFilterDataInputType,
)
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
from apps.notification.models import Notification


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
        serializer = EventUpdateSerializer(
            instance=instance,
            data=data,
            context=dict(request=info.context.request),
            partial=True,
        )
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


class ExportEvents(ExportBaseMutation):
    class Arguments(ExportBaseMutation.Arguments):
        filters = EventFilterDataInputType(required=True)
    DOWNLOAD_TYPE = ExcelDownload.DOWNLOAD_TYPES.EVENT


class ExportActors(ExportBaseMutation):
    class Arguments(ExportBaseMutation.Arguments):
        filters = ActorFilterDataInputType(required=True)
    DOWNLOAD_TYPE = ExcelDownload.DOWNLOAD_TYPES.ACTOR


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
    @permission_checker(['event.add_contextofviolence'])
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
    @permission_checker(['event.change_contextofviolence'])
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
    @permission_checker(['event.delete_contextofviolence'])
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


class SetAssigneeToEvent(graphene.Mutation):
    class Arguments:
        event_id = graphene.ID(required=True)
        user_id = graphene.ID(required=True)
    errors = graphene.List(graphene.NonNull(CustomErrorType))
    ok = graphene.Boolean()
    result = graphene.Field(EventType)

    @staticmethod
    @permission_checker(['event.assign_event'])
    def mutate(root, info, event_id, user_id):
        from apps.users.models import User
        event = Event.objects.filter(id=event_id).first()
        if not event:
            return SetAssigneeToEvent(errors=[
                dict(field='nonFieldErrors', messages=gettext('Event does not exist.'))
            ])

        user = User.objects.filter(id=user_id).first()
        # To prevent users being saved with no permission in event review process. for eg GUEST
        if not user.has_perm('event.self_assign_event'):
            return SetAssigneeToEvent(errors=[
                dict(field='nonFieldErrors', messages=gettext('The user does not exist or has enough permissions.'))
            ])

        prev_assignee_id = event.assignee_id
        prev_assigner_id = event.assigner_id

        event.assignee = user
        event.assigner = info.context.user
        event.assigned_at = timezone.now()
        event.save()

        recipients = []
        if prev_assignee_id:
            recipients.append(prev_assignee_id)
        if prev_assigner_id:
            recipients.append(prev_assigner_id)
        if recipients:
            Notification.send_safe_multiple_notifications(
                event=event,
                recipients=recipients,
                actor=info.context.user,
                type=Notification.Type.EVENT_ASSIGNEE_CLEARED,
            )

        recipients = [user.id]
        if prev_assigner_id:
            recipients.append(prev_assigner_id)
        Notification.send_safe_multiple_notifications(
            event=event,
            recipients=recipients,
            actor=info.context.user,
            type=Notification.Type.EVENT_ASSIGNED,
        )

        return SetAssigneeToEvent(result=event, errors=None, ok=True)


class SetSelfAssigneeToEvent(graphene.Mutation):
    class Arguments:
        event_id = graphene.ID(required=True)
    errors = graphene.List(graphene.NonNull(CustomErrorType))
    ok = graphene.Boolean()
    result = graphene.Field(EventType)

    @staticmethod
    @permission_checker(['event.self_assign_event'])
    def mutate(root, info, event_id):
        event = Event.objects.filter(id=event_id).first()
        if not event:
            return SetSelfAssigneeToEvent(errors=[
                dict(field='nonFieldErrors', messages=gettext('Event does not exist.'))
            ])

        prev_assignee_id = event.assignee_id
        prev_assigner_id = event.assigner_id

        event.assignee = info.context.user
        event.assigner = info.context.user
        event.assigned_at = timezone.now()
        event.save()

        recipients = []
        if prev_assignee_id:
            recipients.append(prev_assignee_id)
        if prev_assigner_id:
            recipients.append(prev_assigner_id)
        if recipients:
            Notification.send_safe_multiple_notifications(
                event=event,
                recipients=recipients,
                actor=info.context.user,
                type=Notification.Type.EVENT_ASSIGNEE_CLEARED,
            )

        recipients = [user['id'] for user in Event.regional_coordinators(
            event,
            actor=info.context.user,
        )]
        if prev_assigner_id:
            recipients.append(prev_assigner_id)
        Notification.send_safe_multiple_notifications(
            recipients=recipients,
            type=Notification.Type.EVENT_SELF_ASSIGNED,
            actor=info.context.user,
            event=event,
        )

        return SetSelfAssigneeToEvent(result=event, errors=None, ok=True)


class ClearAssigneFromEvent(graphene.Mutation):
    class Arguments:
        event_id = graphene.ID(required=True)
    errors = graphene.List(graphene.NonNull(CustomErrorType))
    ok = graphene.Boolean()
    result = graphene.Field(EventType)

    @staticmethod
    @permission_checker(['event.clear_assignee_event'])
    def mutate(root, info, event_id):
        # Admin, assigner and assignee(self) can only clear assignee
        event = Event.objects.filter(id=event_id).first()
        if not event:
            return ClearAssigneFromEvent(errors=[
                dict(field='nonFieldErrors', messages=gettext('Event does not exist.'))
            ])

        prev_assignee_id = event.assignee_id
        prev_assigner_id = event.assigner_id
        if not prev_assignee_id:
            return ClearAssigneFromEvent(errors=[
                dict(
                    field='nonFieldErrors',
                    messages=gettext('Cannot clear assignee because event does not have an assignee'),
                )
            ])

        event.assignee = None
        event.assigner = None
        event.assigned_at = None
        event.save()

        recipients = []
        if prev_assignee_id:
            recipients.append(prev_assignee_id)
        if prev_assigner_id:
            recipients.append(prev_assigner_id)
        if recipients:
            Notification.send_safe_multiple_notifications(
                event=event,
                recipients=recipients,
                actor=info.context.user,
                type=Notification.Type.EVENT_ASSIGNEE_CLEARED,
            )

        return ClearAssigneFromEvent(result=event, errors=None, ok=True)


class ClearSelfAssigneFromEvent(graphene.Mutation):
    class Arguments:
        event_id = graphene.ID(required=True)
    errors = graphene.List(graphene.NonNull(CustomErrorType))
    ok = graphene.Boolean()
    result = graphene.Field(EventType)

    @staticmethod
    @permission_checker(['event.clear_self_assignee_event'])
    def mutate(root, info, event_id):
        event = Event.objects.filter(id=event_id).first()
        if not event:
            return ClearSelfAssigneFromEvent(errors=[
                dict(field='nonFieldErrors', messages=gettext('Event does not exist.'))
            ])

        # Admin and RE can clear all other users from assignee except ME
        # FIXME: this logic does not seem right after `or`
        if event.assignee_id != info.context.user.id or info.context.user.has_perm('clear_assignee_from_event'):
            return ClearAssigneFromEvent(errors=[
                dict(field='nonFieldErrors', messages=gettext('You are not allowed to clear others from assignee.'))
            ])

        prev_assigner_id = event.assigner_id

        event.assignee = None
        event.assigner = None
        event.assigned_at = None
        event.save()

        recipients = []
        if event.regional_coordinators:
            recipients.extend([user['id'] for user in Event.regional_coordinators(
                event,
                actor=info.context.user,
            )])
        if prev_assigner_id:
            recipients.append(prev_assigner_id)

        if recipients:
            Notification.send_safe_multiple_notifications(
                recipients=recipients,
                type=Notification.Type.EVENT_ASSIGNEE_CLEARED,
                actor=info.context.user,
                event=event,
            )

        return ClearSelfAssigneFromEvent(result=event, errors=None, ok=True)


class SignOffEvent(graphene.Mutation):
    class Arguments:
        event_id = graphene.ID(required=True)
    errors = graphene.List(graphene.NonNull(CustomErrorType))
    ok = graphene.Boolean()
    result = graphene.Field(EventType)

    @staticmethod
    @permission_checker(['event.sign_off_event'])
    def mutate(root, info, event_id):
        event = Event.objects.filter(id=event_id).first()
        if not event:
            return SignOffEvent(errors=[
                dict(field='nonFieldErrors', messages=gettext('Event does not exist.'))
            ])
        if not event.review_status == Event.EVENT_REVIEW_STATUS.APPROVED:
            return SignOffEvent(errors=[
                dict(field='nonFieldErrors', messages=gettext('Event is not approved yet.'))
            ])

        event.review_status = Event.EVENT_REVIEW_STATUS.SIGNED_OFF
        event.save()

        recipients = [
            user['id'] for user in Event.regional_coordinators(
                event,
                actor=info.context.user,
            )
        ]
        if event.created_by_id:
            recipients.append(event.created_by_id)
        if event.assignee_id:
            recipients.append(event.assignee_id)

        Notification.send_safe_multiple_notifications(
            recipients=recipients,
            type=Notification.Type.EVENT_SIGNED_OFF,
            actor=info.context.user,
            event=event,
        )

        return SignOffEvent(result=event, errors=None, ok=True)


class ExportContextOfViolences(ExportBaseMutation):
    class Arguments(ExportBaseMutation.Arguments):
        filters = ContextOfViolenceFilterDataInputType(required=True)
    DOWNLOAD_TYPE = ExcelDownload.DOWNLOAD_TYPES.CONTEXT_OF_VIOLENCE


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
    export_context_of_violences = ExportContextOfViolences.Field()
    clone_event = CloneEvent.Field()

    # review related
    set_assignee_to_event = SetAssigneeToEvent.Field()
    set_self_assignee_to_event = SetSelfAssigneeToEvent.Field()
    clear_assignee_from_event = ClearAssigneFromEvent.Field()
    clear_self_assignee_from_event = ClearSelfAssigneFromEvent.Field()
    sign_off_event = SignOffEvent.Field()
