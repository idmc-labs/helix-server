import graphene
from graphene_django.debug import DjangoDebug

from apps.users import schema as user_schema, mutations as user_mutations


class Query(user_schema.Query, graphene.ObjectType):
    debug = graphene.Field(DjangoDebug, name='_debug')


class Mutation(user_mutations.Mutation, graphene.ObjectType):
    pass


schema = graphene.Schema(query=Query, mutation=Mutation)
