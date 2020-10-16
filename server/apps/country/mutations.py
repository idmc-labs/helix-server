import graphene

from apps.country.schema import SummaryType, ContextualUpdateType
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


class CreateSummary(graphene.Mutation):
    class Arguments:
        summary = SummaryCreateInputType(required=True)

    errors = graphene.List(CustomErrorType)
    ok = graphene.Boolean()
    summary = graphene.Field(SummaryType)

    @staticmethod
    @permission_checker(['country.add_summary'])
    def mutate(root, info, summary):
        serializer = SummarySerializer(data=summary,
                                       context={'request': info.context})
        if errors := mutation_is_not_valid(serializer):
            return CreateSummary(errors=errors, ok=False)
        instance = serializer.save()
        return CreateSummary(summary=instance, errors=None, ok=True)


class CreateContextualUpdate(graphene.Mutation):
    class Arguments:
        contextual_update = ContextualUpdateCreateInputType(required=True)

    errors = graphene.List(CustomErrorType)
    ok = graphene.Boolean()
    contextual_update = graphene.Field(ContextualUpdateType)

    @staticmethod
    @permission_checker(['country.add_contextual_update'])
    def mutate(root, info, contextual_update):
        serializer = ContextualUpdateSerializer(data=contextual_update,
                                                context={'request': info.context})
        if errors := mutation_is_not_valid(serializer):
            return CreateContextualUpdate(errors=errors, ok=False)
        instance = serializer.save()
        return CreateContextualUpdate(contextual_update=instance, errors=None, ok=True)


class Mutation:
    create_summary = CreateSummary.Field()
    create_contextual_update = CreateContextualUpdate.Field()
