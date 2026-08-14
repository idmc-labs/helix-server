import graphene
from graphene_file_upload.scalars import Upload

from utils.error_types import CustomErrorType, mutation_is_not_valid
from utils.permissions import is_authenticated, permission_checker

from .enums import HulkBulkImportDatasetImportTypeEnum
from .schema import HulkBulkImportType
from .serializers import HulkBulkImportSerializer


class HulkBulkImportDatasetCreateInputType(graphene.InputObjectType):
    import_type = graphene.Field(HulkBulkImportDatasetImportTypeEnum, required=True)
    import_file = Upload(required=True)


class HulkBulkImportCreateInputType(graphene.InputObjectType):
    name = graphene.String()
    datasets = graphene.List(graphene.NonNull(HulkBulkImportDatasetCreateInputType), required=True)


class TriggerHulkBulkImport(graphene.Mutation):
    class Arguments:
        data = HulkBulkImportCreateInputType(required=True)

    errors = graphene.List(graphene.NonNull(CustomErrorType))
    ok = graphene.Boolean()
    result = graphene.Field(HulkBulkImportType)

    @staticmethod
    @is_authenticated()
    @permission_checker(["hulk.trigger_hulkbulkimport"])
    def mutate(_, info, data):
        serializer = HulkBulkImportSerializer(
            data=data,
            context={"request": info.context.request},
        )
        if errors := mutation_is_not_valid(serializer):
            return TriggerHulkBulkImport(errors=errors, ok=False)
        instance = serializer.save()
        return TriggerHulkBulkImport(result=instance, errors=None, ok=True)


class Mutation:
    trigger_hulk_bulk_import = TriggerHulkBulkImport.Field()
