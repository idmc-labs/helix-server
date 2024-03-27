import graphene
from graphene_django import DjangoObjectType
from graphene_django_extras import (
    DjangoObjectField,
    PageGraphqlPagination,
)
from utils.graphene.enums import EnumDescription

from apps.contrib.models import (
    Attachment,
    ExcelDownload,
    Client,
    ClientTrackInfo,
    BulkApiOperation,
)
from apps.contrib.filters import (
    ClientTrackInfoFilter,
    ClientFilter,
    ExcelExportFilter,
    BulkApiOperationFilter,
)
from apps.contrib.enums import (
    AttachmentForGrapheneEnum,
    DownloadTypeGrapheneEnum,
    ExcelGenerationStatusGrapheneEnum,
    BulkApiOperationActionEnum,
    BulkApiOperationStatusEnum,
)
from apps.contrib.bulk_operations.serializers import BulkApiOperationPayloadSerializer
from apps.extraction.filters import FigureExtractionBulkOperationFilterDataType
from apps.entry.models import ExternalApiDump
from apps.entry.enums import ExternalApiTypeEnum
from apps.contrib.enums import ClientUseCaseEnum
from utils.graphene.types import CustomDjangoListObjectType
from utils.graphene.fields import DjangoPaginatedListObjectField, generate_type_for_serializer
from utils.error_types import CustomErrorType


BulkApiOperationPayloadType = generate_type_for_serializer(
    'BulkApiOperationPayloadType',
    serializer_class=BulkApiOperationPayloadSerializer,
)


class ExcelExportType(DjangoObjectType):
    class Meta:
        model = ExcelDownload

    download_type = graphene.Field(DownloadTypeGrapheneEnum)
    download_type_display = EnumDescription(source='get_download_type_display')
    status = graphene.Field(ExcelGenerationStatusGrapheneEnum)
    status_display = EnumDescription(source='get_status_display')

    def resolve_file(root, info, **kwargs):
        if not getattr(root, 'file', None):
            return None
        return info.context.request.build_absolute_uri(root.file.url)


class ExcelExportsListType(CustomDjangoListObjectType):
    class Meta:
        model = ExcelDownload
        filterset_class = ExcelExportFilter


class ClientType(DjangoObjectType):
    class Meta:
        model = Client
        fields = (
            'id',
            'name',
            'is_active',
            'code',
            'acronym',
            'contact_name',
            'contact_email',
            'contact_website',
            'created_by',
            'created_at',
            'other_notes',
            'opted_out_of_emails',
            'last_modified_by',
            'modified_at',
        )
    use_case = graphene.List(graphene.NonNull(ClientUseCaseEnum))
    use_case_display = EnumDescription(source='get_use_case_display')


class ClientListType(CustomDjangoListObjectType):
    class Meta:
        model = Client
        filterset_class = ClientFilter


class ClientTrackInformationType(DjangoObjectType):
    api_name = graphene.NonNull(graphene.String)

    class Meta:
        model = ClientTrackInfo
        fields = (
            'id',
            'client',
            'api_type',
            'api_name',
            'requests_per_day',
            'tracked_date',
        )

    api_type = graphene.Field(ExternalApiTypeEnum)
    api_type_display = EnumDescription(source='get_api_type_display')

    # Metadata
    response_type = graphene.String(required=True)
    usage = graphene.String(required=True)
    description = graphene.String(required=True)
    example_request = graphene.String(required=True)

    @staticmethod
    def resolve_response_type(root, info, **_):
        return ExternalApiDump.API_TYPE_METADATA[root.api_type].response_type

    @staticmethod
    def resolve_usage(root, info, **_):
        return ExternalApiDump.API_TYPE_METADATA[root.api_type].get_usage(
            info.context.request,
            root.client.code,  # NOTE: Client is select_related using ClientTrackInfoFilter
        )

    @staticmethod
    def resolve_description(root, info, **_):
        return ExternalApiDump.API_TYPE_METADATA[root.api_type].description

    @staticmethod
    def resolve_example_request(root, info, **_):
        return ExternalApiDump.API_TYPE_METADATA[root.api_type].get_example_request(
            info.context.request,
            root.client.code,  # NOTE: Client is select_related using ClientTrackInfoFilter
        )


class ClientTrackInformationListType(CustomDjangoListObjectType):
    class Meta:
        model = ClientTrackInfo
        filterset_class = ClientTrackInfoFilter


class AttachmentType(DjangoObjectType):
    class Meta:
        model = Attachment

    attachment_for = graphene.Field(AttachmentForGrapheneEnum)
    attachment_for_display = EnumDescription(source='get_attachment_for_display')

    def resolve_attachment(root, info, **kwargs):
        return info.context.request.build_absolute_uri(root.attachment.url)


class BulkApiOperationFilterType(graphene.ObjectType):
    # NOTE: This should be same as apps/contribs/serializer::BulkApiOperationFilterSerializer
    figure_role = graphene.Field(
        type(
            'BulkApiOperationFigureRoleFilterType',
            (graphene.ObjectType,),
            dict(
                figure=graphene.Field(FigureExtractionBulkOperationFilterDataType, required=True),
            ),
        )
    )


class BulkApiOperationSuccessType(graphene.ObjectType):
    id = graphene.ID(required=True)
    frontend_url = graphene.String(required=True)
    frontend_permalink_url = graphene.String(required=True)


class BulkApiOperationFailureType(BulkApiOperationSuccessType):
    errors = graphene.List(graphene.NonNull(CustomErrorType), required=True)


class BulkApiOperationObjectType(DjangoObjectType):
    class Meta:
        model = BulkApiOperation
        fields = (
            'id',
            'created_at',
            'created_by',
            'started_at',
            'completed_at',
            'success_count',
            'failure_count',
        )

    action = graphene.Field(BulkApiOperationActionEnum)
    action_display = EnumDescription(source='get_action_display')
    status = graphene.Field(BulkApiOperationStatusEnum, required=True)
    status_display = EnumDescription(source='get_status_display', required=True)
    filters = graphene.Field(BulkApiOperationFilterType, required=True)
    payload = graphene.Field(BulkApiOperationPayloadType, required=True)

    success_list = graphene.List(graphene.NonNull(BulkApiOperationSuccessType), required=True)
    failure_list = graphene.List(graphene.NonNull(BulkApiOperationFailureType), required=True)

    @staticmethod
    def resolve_success_list(root: BulkApiOperation, info, *_) -> int:
        return info.context.bulk_api_operation_success_list_loader.load(root.pk)

    @staticmethod
    def resolve_failure_list(root: BulkApiOperation, info, *_) -> int:
        return info.context.bulk_api_operation_failure_list_loader.load(root.pk)


class BulkApiOperationListType(CustomDjangoListObjectType):
    class Meta:
        model = BulkApiOperation
        filterset_class = BulkApiOperationFilter


class Query:
    attachment = DjangoObjectField(AttachmentType)
    excel_exports = DjangoPaginatedListObjectField(ExcelExportsListType,
                                                   pagination=PageGraphqlPagination(
                                                       page_size_query_param='pageSize'
                                                   ))
    client = DjangoObjectField(ClientType)
    client_list = DjangoPaginatedListObjectField(
        ClientListType,
        pagination=PageGraphqlPagination(
            page_size_query_param='pageSize'
        )
    )
    client_track_information_list = DjangoPaginatedListObjectField(
        ClientTrackInformationListType,
        pagination=PageGraphqlPagination(
            page_size_query_param='pageSize'
        )
    )

    bulk_api_operation = DjangoObjectField(BulkApiOperationObjectType)
    bulk_api_operations = DjangoPaginatedListObjectField(
        BulkApiOperationListType,
        pagination=PageGraphqlPagination(
            page_size_query_param='pageSize',
        )
    )
