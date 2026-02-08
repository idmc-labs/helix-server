import graphene

from apps.contrib.schema import BulkApiOperationObjectType
from utils.error_types import CustomErrorType, mutation_is_not_valid
from utils.mutation import generate_input_type_for_serializer
from utils.permissions import is_authenticated, permission_checker

from .serializers import HulkBulkImportSerializer

HulkBulkImportInputType = generate_input_type_for_serializer(
    "BulkApiOperationInputType",
    serializer_class=HulkBulkImportSerializer,
)


class TriggerHulkBulkImport(graphene.Mutation):
    class Arguments:
        data = HulkBulkImportInputType(required=True)

    errors = graphene.List(graphene.NonNull(CustomErrorType))
    ok = graphene.Boolean()
    result = graphene.Field(BulkApiOperationObjectType)

    @staticmethod
    @is_authenticated()
    @permission_checker(["hulk.add_hulkbulkimport"])
    def mutate(_, info, data):
        serializer = HulkBulkImportSerializer(data=data, context={"request": info.context.request})
        if errors := mutation_is_not_valid(serializer):
            return TriggerHulkBulkImport(errors=errors, ok=False)
        instance = serializer.save()
        return TriggerHulkBulkImport(result=instance, errors=None, ok=True)
