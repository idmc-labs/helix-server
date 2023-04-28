import graphene
from django.db import transaction
from utils.mutation import generate_input_type_for_serializer
from utils.error_types import CustomErrorType, mutation_is_not_valid
from utils.permissions import permission_checker, is_authenticated
from .serializers import StatusLogSerializer, ReleaseMetadataSerializer
from .schema import GiddStatusLogType, GiddReleaseMetadataType
from .tasks import update_gidd_data


class GiddUpdateData(graphene.Mutation):

    errors = graphene.List(graphene.NonNull(CustomErrorType))
    ok = graphene.Boolean()
    result = graphene.Field(GiddStatusLogType)

    @staticmethod
    @is_authenticated()
    @permission_checker(['gidd.update_gidd_data_gidd'])
    def mutate(root, info):
        user = info.context.user
        serializer = StatusLogSerializer(data=dict(triggered_by=user.id))
        if errors := mutation_is_not_valid(serializer):
            return GiddUpdateData(errors=errors, ok=False)
        instance = serializer.save()
        # Update date in background
        transaction.on_commit(lambda: update_gidd_data.delay(log_id=instance.id))
        return GiddUpdateData(result=instance, errors=None, ok=True)


GiddReleaseMetadataInputType = generate_input_type_for_serializer(
    'ReleaseMetadataInputType',
    ReleaseMetadataSerializer,
)


class GiddUpdateReleaseMetaData(graphene.Mutation):

    class Arguments:
        data = GiddReleaseMetadataInputType(required=True)

    errors = graphene.List(graphene.NonNull(CustomErrorType))
    ok = graphene.Boolean()
    result = graphene.Field(GiddReleaseMetadataType)

    @staticmethod
    @is_authenticated()
    @permission_checker(['gidd.update_release_meta_data_gidd'])
    def mutate(root, info, data):
        serializer = ReleaseMetadataSerializer(data=data, context={'request': info.context.request})
        if errors := mutation_is_not_valid(serializer):
            return GiddUpdateReleaseMetaData(errors=errors, ok=False)
        instance = serializer.save()
        # Update date in background
        transaction.on_commit(lambda: update_gidd_data.delay(log_id=instance.id))
        return GiddUpdateReleaseMetaData(result=instance, errors=None, ok=True)


class Mutation(object):
    gidd_update_data = GiddUpdateData.Field()
    gidd_update_release_meta_data = GiddUpdateReleaseMetaData.Field()
