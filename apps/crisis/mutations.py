from django.utils.translation import gettext
import graphene

from apps.contrib.serializers import ExcelDownloadSerializer
from apps.crisis.models import Crisis
from apps.crisis.filters import CrisisFilterDataInputType
from apps.crisis.schema import CrisisType
from apps.crisis.serializers import CrisisSerializer, CrisisUpdateSerializer
from utils.error_types import CustomErrorType, mutation_is_not_valid
from utils.permissions import permission_checker
from utils.mutation import generate_input_type_for_serializer
from utils.common import convert_date_object_to_string_in_dict

CrisisCreateInputType = generate_input_type_for_serializer(
    'CrisisCreateInputType',
    CrisisSerializer
)

CrisisUpdateInputType = generate_input_type_for_serializer(
    'CrisisUpdateInputType',
    CrisisUpdateSerializer,
)


class CreateCrisis(graphene.Mutation):
    class Arguments:
        data = CrisisCreateInputType(required=True)

    errors = graphene.List(graphene.NonNull(CustomErrorType))
    ok = graphene.Boolean()
    result = graphene.Field(CrisisType)

    @staticmethod
    @permission_checker(['crisis.add_crisis'])
    def mutate(root, info, data):
        serializer = CrisisSerializer(data=data, context=dict(request=info.context.request))
        if errors := mutation_is_not_valid(serializer):
            return CreateCrisis(errors=errors, ok=False)
        instance = serializer.save()
        return CreateCrisis(result=instance, errors=None, ok=True)


class UpdateCrisis(graphene.Mutation):
    class Arguments:
        data = CrisisUpdateInputType(required=True)

    errors = graphene.List(graphene.NonNull(CustomErrorType))
    ok = graphene.Boolean()
    result = graphene.Field(CrisisType)

    @staticmethod
    @permission_checker(['crisis.change_crisis'])
    def mutate(root, info, data):
        try:
            instance = Crisis.objects.get(id=data['id'])
        except Crisis.DoesNotExist:
            return UpdateCrisis(errors=[
                dict(field='nonFieldErrors', messages=gettext('Crisis does not exist.'))
            ])
        serializer = CrisisSerializer(
            instance=instance,
            data=data,
            context=dict(request=info.context),
            partial=True
        )
        if errors := mutation_is_not_valid(serializer):
            return UpdateCrisis(errors=errors, ok=False)
        instance = serializer.save()
        return UpdateCrisis(result=instance, errors=None, ok=True)


class DeleteCrisis(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    errors = graphene.List(graphene.NonNull(CustomErrorType))
    ok = graphene.Boolean()
    result = graphene.Field(CrisisType)

    @staticmethod
    @permission_checker(['crisis.delete_crisis'])
    def mutate(root, info, id):
        try:
            instance = Crisis.objects.get(id=id)
        except Crisis.DoesNotExist:
            return DeleteCrisis(errors=[
                dict(field='nonFieldErrors', messages=gettext('Crisis does not exist.'))
            ])
        instance.delete()
        instance.id = id
        return DeleteCrisis(result=instance, errors=None, ok=True)


class ExportCrises(graphene.Mutation):
    class Arguments:
        filters = CrisisFilterDataInputType(required=True)

    errors = graphene.List(graphene.NonNull(CustomErrorType))
    ok = graphene.Boolean()

    @staticmethod
    def mutate(_, info, filters):
        from apps.contrib.models import ExcelDownload

        serializer = ExcelDownloadSerializer(
            data=dict(
                download_type=int(ExcelDownload.DOWNLOAD_TYPES.CRISIS),
                filters=convert_date_object_to_string_in_dict(filters),
            ),
            context=dict(request=info.context.request)
        )
        if errors := mutation_is_not_valid(serializer):
            return ExportCrises(errors=errors, ok=False)
        serializer.save()
        return ExportCrises(errors=None, ok=True)


class Mutation(object):
    create_crisis = CreateCrisis.Field()
    update_crisis = UpdateCrisis.Field()
    delete_crisis = DeleteCrisis.Field()
    export_crises = ExportCrises.Field()
