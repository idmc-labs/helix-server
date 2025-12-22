import typing

import graphene
from django.core.exceptions import PermissionDenied
from django.utils.translation import gettext
from graphene_file_upload.scalars import Upload

from apps.contrib.bulk_operations.serializers import BulkApiOperationSerializer
from apps.contrib.filters import ClientFilterDataInputType
from apps.contrib.models import (
    Attachment,
    Client,
    ExcelDownload,
)
from apps.contrib.schema import AttachmentType, BulkApiOperationObjectType, ClientType
from apps.contrib.serializers import (
    AttachmentSerializer,
    BigAttachmentSerializer,
    ClientSerializer,
    ClientUpdateSerializer,
    ExcelDownloadSerializer,
    MarkBigAttachmentFileUploadedSerializer,
)
from utils.common import convert_date_object_to_string_in_dict
from utils.error_types import CustomErrorType, mutation_is_not_valid
from utils.mutation import generate_input_type_for_serializer
from utils.permissions import PERMISSION_DENIED_MESSAGE, is_authenticated, permission_checker

from .filters import ClientTrackInfoFilterDataInputType

BulkApiOperationInputType = generate_input_type_for_serializer(
    "BulkApiOperationInputType",
    serializer_class=BulkApiOperationSerializer,
)


class AttachmentCreateInputType(graphene.InputObjectType):
    attachment = Upload(required=True)
    attachment_for = graphene.String(required=True)


class BigAttachmentCreateInputType(graphene.InputObjectType):
    file_name = graphene.String(required=True)
    attachment_for = graphene.String(required=True)
    mimetype = graphene.String(required=True)


class CreateAttachment(graphene.Mutation):
    class Arguments:
        data = AttachmentCreateInputType(required=True)

    errors = graphene.List(CustomErrorType)
    ok = graphene.Boolean()
    result = graphene.Field(AttachmentType)

    @staticmethod
    @is_authenticated()
    def mutate(root, info, data):
        serializer = AttachmentSerializer(data=data, context={"request": info.context.request})
        if errors := mutation_is_not_valid(serializer):
            return CreateAttachment(errors=errors, ok=False)
        instance = serializer.save()
        return CreateAttachment(result=instance, errors=None, ok=True)


class CreateBigAttachment(graphene.Mutation):
    class Arguments:
        data = BigAttachmentCreateInputType(required=True)

    errors = graphene.List(CustomErrorType)
    ok = graphene.Boolean()
    result = graphene.Field(AttachmentType)
    s3_presigned_upload_url = graphene.String(required=False)

    @staticmethod
    @is_authenticated()
    def mutate(root, info, data):
        serializer = BigAttachmentSerializer(data=data, context={"request": info.context.request})
        if errors := mutation_is_not_valid(serializer):
            return CreateBigAttachment(errors=errors, ok=False)
        instance = serializer.save()
        return CreateBigAttachment(
            result=instance,
            s3_presigned_upload_url=serializer.data.get("s3_presigned_upload_url"),
            errors=None,
            ok=True,
        )


class MarkBigAttachmentFileAsUploaded(graphene.Mutation):
    class Arguments:
        attachment_id = graphene.ID(required=True)

    errors = graphene.List(CustomErrorType)
    ok = graphene.Boolean()
    result = graphene.Field(AttachmentType)

    @staticmethod
    @is_authenticated()
    def mutate(root, info, attachment_id):
        attachment = Attachment.objects.filter(id=attachment_id).first()
        if not attachment:
            return MarkBigAttachmentFileAsUploaded(
                errors=[dict(field="nonFieldErrors", messages=gettext("Attachment does not exist."))]
            )
        if attachment.created_by != info.context.request.user:
            raise PermissionDenied(gettext(PERMISSION_DENIED_MESSAGE))
        serializer = MarkBigAttachmentFileUploadedSerializer(
            instance=attachment, data={}, context={"request": info.context.request}
        )
        if errors := mutation_is_not_valid(serializer):
            return MarkBigAttachmentFileAsUploaded(errors=errors, ok=False)
        instance = serializer.save()

        return MarkBigAttachmentFileAsUploaded(result=instance, errors=None, ok=True)


ClientCreateInputType = generate_input_type_for_serializer(
    "ClientCreateInputType",
    ClientSerializer,
)

ClientUpdateInputType = generate_input_type_for_serializer(
    "ClientUpdateInputType",
    ClientUpdateSerializer,
)


class CreateClient(graphene.Mutation):
    class Arguments:
        data = ClientCreateInputType(required=True)

    errors = graphene.List(CustomErrorType)
    ok = graphene.Boolean()
    result = graphene.Field(ClientType)

    @staticmethod
    @permission_checker(["contrib.add_client"])
    def mutate(root, info, data):
        serializer = ClientSerializer(data=data, context={"request": info.context.request})
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
    @permission_checker(["contrib.change_client"])
    def mutate(root, info, data):
        try:
            instance = Client.objects.get(id=data["id"])
        except Client.DoesNotExist:
            return ClientUpdateSerializer(errors=[dict(field="nonFieldErrors", messages=gettext("Client does not exist."))])
        serializer = ClientUpdateSerializer(instance=instance, data=data, context=dict(request=info.context), partial=True)
        if errors := mutation_is_not_valid(serializer):
            return UpdateClient(errors=errors, ok=False)
        instance = serializer.save()
        return UpdateClient(result=instance, errors=None, ok=True)


class ExportBaseMutation(graphene.Mutation, abstract=True):
    class Arguments: ...

    errors = graphene.List(graphene.NonNull(CustomErrorType))
    ok = graphene.Boolean()

    DOWNLOAD_TYPE: typing.ClassVar[ExcelDownload.DOWNLOAD_TYPES]

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        errors = []
        if not hasattr(cls, "DOWNLOAD_TYPE"):
            errors.append(f"{cls.__name__} must have a 'DOWNLOAD_TYPE' attribute")
        if not hasattr(cls.Arguments, "filters"):
            errors.append(f"{cls.__name__} must have a 'Arguments.filters' attribute")
        elif isinstance(getattr(cls.Arguments, "filters"), graphene.InputField):
            errors.append(f"{cls.__name__} must have a 'Arguments.filters' attribute as InputField")
        if errors:
            raise TypeError(errors)

    @classmethod
    def mutate(cls, _, info, filters):
        serializer = ExcelDownloadSerializer(
            data=dict(
                download_type=int(cls.DOWNLOAD_TYPE),
                filters=convert_date_object_to_string_in_dict(filters),
            ),
            context=dict(request=info.context.request),
        )
        if errors := mutation_is_not_valid(serializer):
            return cls(errors=errors, ok=False)
        serializer.save()
        return cls(errors=None, ok=True)


class ExportTrackingData(ExportBaseMutation):
    class Arguments(ExportBaseMutation.Arguments):
        filters = ClientTrackInfoFilterDataInputType(required=True)

    DOWNLOAD_TYPE = ExcelDownload.DOWNLOAD_TYPES.TRACKING_DATA


class ExportClients(ExportBaseMutation):
    """
    A mutation for exporting client data based on provided filters.
    Utilizes the DOWNLOAD_TYPE attribute to specify the type of data to be exported.
    """

    class Arguments:
        filters = ClientFilterDataInputType(required=True)

    DOWNLOAD_TYPE = ExcelDownload.DOWNLOAD_TYPES.CLIENT


class TriggerBulkOperation(graphene.Mutation):
    class Arguments:
        data = BulkApiOperationInputType(required=True)

    errors = graphene.List(graphene.NonNull(CustomErrorType))
    ok = graphene.Boolean()
    result = graphene.Field(BulkApiOperationObjectType)

    @staticmethod
    # TODO: Define a proper permission
    # For now, this is handle at client level.
    # We do handle the permission internally as well.
    def mutate(_, info, data):
        serializer = BulkApiOperationSerializer(data=data, context={"request": info.context.request})
        if errors := mutation_is_not_valid(serializer):
            return TriggerBulkOperation(errors=errors, ok=False)
        instance = serializer.save()
        return TriggerBulkOperation(result=instance, errors=None, ok=True)


class Mutation:
    create_attachment = CreateAttachment.Field()
    create_big_attachment = CreateBigAttachment.Field()
    mark_big_attachment_file_as_uploaded = MarkBigAttachmentFileAsUploaded.Field()
    create_client = CreateClient.Field()
    update_client = UpdateClient.Field()
    export_tracking_data = ExportTrackingData.Field()
    export_clients = ExportClients.Field()
    trigger_bulk_operation = TriggerBulkOperation.Field()
