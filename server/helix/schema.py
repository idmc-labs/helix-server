import graphene

from apps.users import schema as user_schema, mutations as user_mutations
from apps.contact import schema as contact_schema, mutations as contact_mutations


class Query(user_schema.Query,
            contact_schema.Query,
            graphene.ObjectType):
    pass


class Mutation(user_mutations.Mutation,
               contact_mutations.Mutation,
               graphene.ObjectType):
    pass


schema = graphene.Schema(query=Query, mutation=Mutation)
