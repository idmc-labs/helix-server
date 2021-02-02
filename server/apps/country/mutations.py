import graphene

from apps.country.schema import SummaryType, ContextualUpdateType
from apps.crisis.enums import CrisisTypeGrapheneEnum

from apps.country.serializers import SummarySerializer, ContextualUpdateSerializer
from utils.error_types import CustomErrorType, mutation_is_not_valid
from utils.permissions import permission_checker


class SummaryCreateInputType(graphene.InputObjectType):
    """
    Crisis Create InputType
    """
    summary = graphene.String(required=True)
    country = graphene.ID(required=True)


class ContextualUpdateCreateInputType(graphene.InputObjectType):
    """
    Crisis Create InputType
    """
    update = graphene.String(required=True)
    country = graphene.ID(required=True)
    publish_date = graphene.Date()
    crisis_type = graphene.NonNull(CrisisTypeGrapheneEnum)


class CreateSummary(graphene.Mutation):
    class Arguments:
        data = SummaryCreateInputType(required=True)

    errors = graphene.List(graphene.NonNull(CustomErrorType))
    ok = graphene.Boolean()
    result = graphene.Field(SummaryType)

    @staticmethod
    @permission_checker(['country.add_summary'])
    def mutate(root, info, data):
        serializer = SummarySerializer(data=data,
                                       context={'request': info.context})
        if errors := mutation_is_not_valid(serializer):
            return CreateSummary(errors=errors, ok=False)
        instance = serializer.save()
        return CreateSummary(result=instance, errors=None, ok=True)


class CreateContextualUpdate(graphene.Mutation):
    class Arguments:
        data = ContextualUpdateCreateInputType(required=True)

    errors = graphene.List(graphene.NonNull(CustomErrorType))
    ok = graphene.Boolean()
    result = graphene.Field(ContextualUpdateType)

    @staticmethod
    @permission_checker(['country.add_contextualupdate'])
    def mutate(root, info, data):
        serializer = ContextualUpdateSerializer(data=data,
                                                context={'request': info.context})
        if errors := mutation_is_not_valid(serializer):
            return CreateContextualUpdate(errors=errors, ok=False)
        instance = serializer.save()
        return CreateContextualUpdate(result=instance, errors=None, ok=True)


class Mutation:
    create_summary = CreateSummary.Field()
    create_contextual_update = CreateContextualUpdate.Field()
