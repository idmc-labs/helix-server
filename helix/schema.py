import graphene
from graphene_django.debug import DjangoDebug

from apps.contact import mutations as contact_mutations
from apps.contact import schema as contact_schema
from apps.contextualupdate import mutations as contextual_update_mutations
from apps.contextualupdate import schema as contextual_update_schema
from apps.contrib import mutations as contrib_mutations
from apps.contrib import schema as contrib_schema
from apps.country import mutations as country_mutation
from apps.country import schema as country_schema
from apps.crisis import mutations as crisis_mutations
from apps.crisis import schema as crisis_schema
from apps.entry import mutations as entry_mutations
from apps.entry import schema as entry_schema
from apps.event import mutations as event_mutations
from apps.event import schema as event_schema
from apps.extraction import mutations as extraction_mutations
from apps.extraction import schema as extraction_schema
from apps.gidd import enums as gidd_enums
from apps.gidd import mutations as gidd_mutations
from apps.gidd import schema as gidd_schema
from apps.notification import mutations as notification_mutations
from apps.notification import schema as notification_schema
from apps.organization import mutations as organization_mutations
from apps.organization import schema as organization_schema
from apps.parking_lot import mutations as parking_lot_mutations
from apps.parking_lot import schema as parking_lot_schema
from apps.report import enums as report_enums
from apps.report import mutations as report_mutations
from apps.report import schema as report_schema
from apps.resource import mutations as resource_mutations
from apps.resource import schema as resource_schema
from apps.review import mutations as review_mutations
from apps.review import schema as review_schema
from apps.users import mutations as user_mutations
from apps.users import schema as user_schema


class Query(
    user_schema.Query,
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
    notification_schema.Query,
    gidd_schema.Query,
    graphene.ObjectType,
):
    debug = graphene.Field(DjangoDebug, name="_debug")


class Mutation(
    user_mutations.Mutation,
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
    notification_mutations.Mutation,
    gidd_mutations.Mutation,
    graphene.ObjectType,
):
    pass


class Enum(report_enums.ReportEnumType, gidd_enums.GiddEnumType, graphene.ObjectType):
    pass


schema = graphene.Schema(query=Query, mutation=Mutation, types=[Enum])
