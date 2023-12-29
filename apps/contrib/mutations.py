import graphene
from graphene_file_upload.scalars import Upload
from django.utils.translation import gettext
from utils.mutation import generate_input_type_for_serializer
from graphene_django.filter.utils import get_filtering_args_from_filterset

from apps.contrib.serializers import ExcelDownloadSerializer
from utils.common import convert_date_object_to_string_in_dict
from apps.contrib.schema import AttachmentType, ClientType, BulkApiOperationType
from apps.contrib.bulk_operations.serializers import BulkApiOperationSerializer
from apps.contrib.serializers import (
    AttachmentSerializer,
    ClientSerializer,
    ClientUpdateSerializer,
)
from apps.contrib.models import (
    Client,
)
from .filters import ClientTrackInfoFilter
from .schema import ClientTrackInformationType
from utils.error_types import CustomErrorType, mutation_is_not_valid
from utils.permissions import is_authenticated, permission_checker


BulkApiOperationInputType = generate_input_type_for_serializer(
    'BulkApiOperationInputType',
    serializer_class=BulkApiOperationSerializer,
)


class AttachmentCreateInputType(graphene.InputObjectType):
    attachment = Upload(required=True)
    attachment_for = graphene.String(required=True)


class CreateAttachment(graphene.Mutation):
    class Arguments:
        data = AttachmentCreateInputType(required=True)

    errors = graphene.List(CustomErrorType)
    ok = graphene.Boolean()
    result = graphene.Field(AttachmentType)

    @staticmethod
    @is_authenticated()
    def mutate(root, info, data):
        serializer = AttachmentSerializer(data=data,
                                          context={'request': info.context.request})
        if errors := mutation_is_not_valid(serializer):
            return CreateAttachment(errors=errors, ok=False)
        instance = serializer.save()
        return CreateAttachment(result=instance, errors=None, ok=True)


ClientCreateInputType = generate_input_type_for_serializer(
    'clientCreateInputType',
    ClientSerializer
)

ClientUpdateInputType = generate_input_type_for_serializer(
    'ClientUpdateInputType',
    ClientUpdateSerializer,
)


class CreateClient(graphene.Mutation):
    class Arguments:
        data = ClientCreateInputType(required=True)

    errors = graphene.List(CustomErrorType)
    ok = graphene.Boolean()
    result = graphene.Field(ClientType)

    @staticmethod
    @permission_checker(['contrib.add_client'])
    def mutate(root, info, data):
        serializer = ClientSerializer(
            data=data,
            context={'request': info.context.request}
        )
        if errors := mutation_is_not_valid(serializer):
            return CreateClient(errors=errors, ok=False)
        instance = serializer.save()
        return CreateClient(result=instance, errors=None, ok=True)


class UpdateClient(graphene.Mutation):
    class Arguments:
        data = ClientUpdateInputType(required=True)

    errors = graphene.List(graphene.NonNull(CustomErrorType))
    ok = graphene.Boolean()
    result = graphene.Field(ClientType)

    @staticmethod
    @permission_checker(['contrib.change_client'])
    def mutate(root, info, data):
        try:
            instance = Client.objects.get(id=data['id'])
        except Client.DoesNotExist:
            return ClientUpdateSerializer(errors=[
                dict(field='nonFieldErrors', messages=gettext('Client does not exist.'))
            ])
        serializer = ClientUpdateSerializer(
            instance=instance,
            data=data,
            context=dict(request=info.context),
            partial=True
        )
        if errors := mutation_is_not_valid(serializer):
            return UpdateClient(errors=errors, ok=False)
        instance = serializer.save()
        return UpdateClient(result=instance, errors=None, ok=True)


class ExportTrackingData(graphene.Mutation):
    class Meta:
        arguments = get_filtering_args_from_filterset(
            ClientTrackInfoFilter,
            ClientTrackInformationType,
        )

    errors = graphene.List(graphene.NonNull(CustomErrorType))
    ok = graphene.Boolean()

    @staticmethod
    def mutate(root, info, **kwargs):
        from apps.contrib.models import ExcelDownload

        serializer = ExcelDownloadSerializer(
            data=dict(
                download_type=int(ExcelDownload.DOWNLOAD_TYPES.TRACKING_DATA),
                filters=convert_date_object_to_string_in_dict(kwargs),
            ),
            context=dict(request=info.context.request)
        )
        if errors := mutation_is_not_valid(serializer):
            return ExportTrackingData(errors=errors, ok=False)
        serializer.save()
        return ExportTrackingData(errors=None, ok=True)


class TriggerBulkOperation(graphene.Mutation):
    class Arguments:
        data = BulkApiOperationInputType(required=True)

    errors = graphene.List(graphene.NonNull(CustomErrorType))
    ok = graphene.Boolean()
    result = graphene.Field(BulkApiOperationType, required=True)

    @staticmethod
    # @permission_checker(['entry.add_entry'])
    def mutate(_, info, data):
        serializer = BulkApiOperationSerializer(data=data, context={'request': info.context.request})
        if errors := mutation_is_not_valid(serializer):
            return TriggerBulkOperation(errors=errors, ok=False)
        instance = serializer.save()
        return TriggerBulkOperation(result=instance, errors=None, ok=True)


class Mutation:
    create_attachment = CreateAttachment.Field()
    create_client = CreateClient.Field()
    update_client = UpdateClient.Field()
    export_tracking_data = ExportTrackingData.Field()
    trigger_bulk_operation = TriggerBulkOperation.Field()
