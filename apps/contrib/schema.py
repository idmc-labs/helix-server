import graphene
from graphene_django import DjangoObjectType
from graphene_django_extras import (
    DjangoObjectField,
    PageGraphqlPagination,
)
from utils.graphene.enums import EnumDescription

from apps.contrib.models import Attachment, ExcelDownload, Client, ClientTrackInfo
from apps.contrib.filters import ClientTrackInfoFilter, ClientFilter
from apps.contrib.filters import ExcelExportFilter
from apps.contrib.enums import (
    AttachmentForGrapheneEnum,
    DownloadTypeGrapheneEnum,
    ExcelGenerationStatusGrapheneEnum,
)
from apps.entry.enums import ExternalApiTypeEnum
from utils.graphene.types import CustomDjangoListObjectType
from utils.graphene.fields import DjangoPaginatedListObjectField


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
            'created_by',
            'last_modified_by',
        )


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
