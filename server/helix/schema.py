import graphene
from graphene_django.debug import DjangoDebug

from apps.users import schema as user_schema, mutations as user_mutations
from apps.contact import schema as contact_schema, mutations as contact_mutations
from apps.organization import schema as organization_schema, mutations as organization_mutations
from apps.country import schema as country_schema, mutations as country_mutation
from apps.crisis import schema as crisis_schema, mutations as crisis_mutations
from apps.event import schema as event_schema, mutations as event_mutations
from apps.entry import schema as entry_schema, mutations as entry_mutations


class Query(user_schema.Query,
            contact_schema.Query,
            organization_schema.Query,
            country_schema.Query,
            crisis_schema.Query,
            event_schema.Query,
            entry_schema.Query,
            graphene.ObjectType):
    debug = graphene.Field(DjangoDebug, name='_debug')


class Mutation(user_mutations.Mutation,
               contact_mutations.Mutation,
               country_mutation.Mutation,
               organization_mutations.Mutation,
               crisis_mutations.Mutation,
               event_mutations.Mutation,
               entry_mutations.Mutation,
               graphene.ObjectType):
    pass


schema = graphene.Schema(query=Query, mutation=Mutation)
