import graphene
from graphene_django.debug import DjangoDebug

from apps.users import schema as user_schema, mutations as user_mutations
from apps.contact import schema as contact_schema, mutations as contact_mutations
from apps.contrib import schema as contrib_schema, mutations as contrib_mutations
from apps.organization import schema as organization_schema, mutations as organization_mutations
from apps.country import schema as country_schema, mutations as country_mutation
from apps.crisis import schema as crisis_schema, mutations as crisis_mutations
from apps.event import schema as event_schema, mutations as event_mutations
from apps.entry import schema as entry_schema, mutations as entry_mutations
from apps.extraction import schema as extraction_schema, mutations as extraction_mutations
from apps.report import schema as report_schema, mutations as report_mutations, enums as report_enums
from apps.resource import schema as resource_schema, mutations as resource_mutations
from apps.review import schema as review_schema, mutations as review_mutations
from apps.contextualupdate import (
    schema as contextual_update_schema,
    mutations as contextual_update_mutations
)
from apps.parking_lot import schema as parking_lot_schema, mutations as parking_lot_mutations


class Query(user_schema.Query,
            contact_schema.Query,
            contrib_schema.Query,
            organization_schema.Query,
            country_schema.Query,
            crisis_schema.Query,
            event_schema.Query,
            entry_schema.Query,
            extraction_schema.Query,
            resource_schema.Query,
            review_schema.Query,
            parking_lot_schema.Query,
            contextual_update_schema.Query,
            report_schema.Query,
            graphene.ObjectType):
    debug = graphene.Field(DjangoDebug, name='_debug')


class Mutation(user_mutations.Mutation,
               contact_mutations.Mutation,
               contrib_mutations.Mutation,
               country_mutation.Mutation,
               organization_mutations.Mutation,
               crisis_mutations.Mutation,
               event_mutations.Mutation,
               entry_mutations.Mutation,
               extraction_mutations.Mutation,
               report_mutations.Mutation,
               resource_mutations.Mutation,
               review_mutations.Mutation,
               parking_lot_mutations.Mutation,
               contextual_update_mutations.Mutation,
               graphene.ObjectType):
    pass


class Enum(report_enums.ReportEnumType,
           graphene.ObjectType):
    pass


schema = graphene.Schema(query=Query, mutation=Mutation, types=[Enum])
