import graphene

from apps.users import schema as user_schema, mutations as user_mutations


class Query(user_schema.Query, graphene.ObjectType):
    pass


class Mutation(user_mutations.Mutation, graphene.ObjectType):
    pass


schema = graphene.Schema(query=Query, mutation=Mutation)
