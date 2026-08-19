import graphene
from graphene_django import DjangoObjectType

from utils.graphene.enums import EnumDescription
from utils.graphene.fields import DjangoPaginatedListObjectField
from utils.graphene.pagination import GatedPageGraphqlPagination
from utils.graphene.types import CustomDjangoListObjectType
from utils.permissions import is_authenticated

from .enums import HulkBulkImportDatasetImportTypeEnum, HulkBulkImportStatusEnum
from .filters import HulkBulkImportFilter
from .models import HulkBulkImport, HulkBulkImportDataset


class HulkBulkImportDatasetType(DjangoObjectType):
    class Meta:
        model = HulkBulkImportDataset
        fields = (
            "id",
            "bulk_import",
            "created_at",
            "success_count",
            "failure_count",
            "skip_count",
        )

    import_type = graphene.Field(HulkBulkImportDatasetImportTypeEnum, required=True)
    import_type_display = EnumDescription(source="get_import_type_display", required=True)

    # File URLs — graphene-django's default FileField → graphene.String
    # converter returns the raw storage key. Mirror the helix-wide pattern
    # used by AttachmentType / ExcelDownloadType / ReportType: each FileField
    # gets its own resolver returning ``request.build_absolute_uri(field.url)``.
    import_file = graphene.String()
    success_file = graphene.String()
    failure_file = graphene.String()
    skip_file = graphene.String()

    def resolve_import_file(root, info, **kwargs):
        if not root.import_file:
            return None
        return info.context.request.build_absolute_uri(root.import_file.url)

    def resolve_success_file(root, info, **kwargs):
        if not root.success_file:
            return None
        return info.context.request.build_absolute_uri(root.success_file.url)

    def resolve_failure_file(root, info, **kwargs):
        if not root.failure_file:
            return None
        return info.context.request.build_absolute_uri(root.failure_file.url)

    def resolve_skip_file(root, info, **kwargs):
        if not root.skip_file:
            return None
        return info.context.request.build_absolute_uri(root.skip_file.url)


class HulkBulkImportType(DjangoObjectType):
    class Meta:
        model = HulkBulkImport
        fields = (
            "id",
            "name",
            "created_at",
            "created_by",
            "started_at",
            "completed_at",
        )

    status = graphene.Field(HulkBulkImportStatusEnum, required=True)
    status_display = EnumDescription(source="get_status_display", required=True)

    # Aggregates are computed on read from the dataset rows — there's no
    # denormalised column on HulkBulkImport itself.
    success_count = graphene.Int()
    failure_count = graphene.Int()
    skip_count = graphene.Int()
    datasets = graphene.List(graphene.NonNull(HulkBulkImportDatasetType))

    def resolve_success_count(root, info, **kwargs):
        return info.context.hulk_bulk_import_success_count_loader.load(root.pk)

    def resolve_failure_count(root, info, **kwargs):
        return info.context.hulk_bulk_import_failure_count_loader.load(root.pk)

    def resolve_skip_count(root, info, **kwargs):
        return info.context.hulk_bulk_import_skip_count_loader.load(root.pk)

    def resolve_datasets(root, info, **kwargs):
        return info.context.hulk_bulk_import_datasets_loader.load(root.pk)


class HulkBulkImportListType(CustomDjangoListObjectType):
    class Meta:
        model = HulkBulkImport
        filterset_class = HulkBulkImportFilter


class Query:
    hulk_bulk_import = graphene.Field(HulkBulkImportType, id=graphene.ID(required=True))
    hulk_bulk_imports = DjangoPaginatedListObjectField(
        HulkBulkImportListType,
        pagination=GatedPageGraphqlPagination(page_size_query_param="pageSize"),
    )

    @staticmethod
    @is_authenticated()
    def resolve_hulk_bulk_import(_, info, id):
        return HulkBulkImport.objects.filter(pk=id).first()
