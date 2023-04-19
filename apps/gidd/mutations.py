import graphene
from utils.mutation import generate_input_type_for_serializer
from utils.error_types import CustomErrorType, mutation_is_not_valid
from utils.permissions import permission_checker, is_authenticated
from .serializers import GiddLogSerializer
from .schema import GiddLogType
from .tasks import update_gidd_data


GiddLogInputType = generate_input_type_for_serializer(
    'GiddLogInputType',
    GiddLogSerializer,
)


class UpdateGiddData(graphene.Mutation):

    errors = graphene.List(graphene.NonNull(CustomErrorType))
    ok = graphene.Boolean()
    result = graphene.Field(GiddLogType)

    @staticmethod
    @is_authenticated()
    @permission_checker(['gidd.update_gidd_data'])
    def mutate(root, info):
        user = info.context.user
        serializer = GiddLogSerializer(data=dict(triggered_by=user.id))
        if errors := mutation_is_not_valid(serializer):
            return UpdateGiddData(errors=errors, ok=False)
        instance = serializer.save()
        # Update date in background
        update_gidd_data.delay(log_id=instance.id)
        return UpdateGiddData(result=instance, errors=None, ok=True)


class Mutation(object):
    gidd_update_data = UpdateGiddData.Field()
