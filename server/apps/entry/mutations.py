import graphene

from apps.entry.enums import QuantifierGrapheneEnum, RoleGrapheneEnum, TypeGrapheneEnum, \
    TermGrapheneEnum, UnitGrapheneEnum
from apps.entry.models import Entry, Figure
from apps.entry.schema import EntryType
from apps.entry.serializers import EntrySerializer
from utils.error_types import CustomErrorType, mutation_is_not_valid
from utils.permissions import permission_checker


class EntryCreateInputType(graphene.InputObjectType):
    url = graphene.String()
    article_title = graphene.String(required=True)
    source = graphene.String(required=True)
    publisher = graphene.String(required=True)
    publish_date = graphene.Date(required=True)
    source_methodology = graphene.String()
    source_excerpt = graphene.String()
    source_breakdown = graphene.String()
    event = graphene.ID(required=True)
    # figures = graphene.List(FigureCreateInputType)
    idmc_analysis = graphene.String()
    methodology = graphene.String()
    tags = graphene.List(graphene.String, required=False)
    reviewers = graphene.List(graphene.ID)


class EntryUpdateInputType(graphene.InputObjectType):
    id = graphene.ID()
    url = graphene.String()
    article_title = graphene.String()
    source = graphene.String()
    publisher = graphene.String()
    publish_date = graphene.Date()
    source_methodology = graphene.String()
    source_excerpt = graphene.String()
    source_breakdown = graphene.String()
    event = graphene.ID()
    idmc_analysis = graphene.String()
    methodology = graphene.String()
    tags = graphene.List(graphene.String)
    reviewers = graphene.List(graphene.ID)


class CreateEntry(graphene.Mutation):
    class Arguments:
        entry = EntryCreateInputType(required=True)

    errors = graphene.List(CustomErrorType)
    ok = graphene.Boolean()
    entry = graphene.Field(EntryType)

    @staticmethod
    def mutate(root, info, entry):
        serializer = EntrySerializer(data=entry)
        if errors := mutation_is_not_valid(serializer):
            return CreateEntry(errors=errors, ok=False)
        instance = serializer.save()
        return CreateEntry(entry=instance, errors=None, ok=True)


class UpdateEntry(graphene.Mutation):
    class Arguments:
        entry = EntryUpdateInputType(required=True)

    errors = graphene.List(CustomErrorType)
    ok = graphene.Boolean()
    entry = graphene.Field(EntryType)

    @staticmethod
    @permission_checker(['entry.change_entry'])
    def mutate(root, info, entry):
        try:
            instance = Entry.objects.get(id=entry['id'])
        except Entry.DoesNotExist:
            return UpdateEntry(errors=[
                CustomErrorType(field='non_field_errors', messages=['Entry Does Not Exist.'])
            ])
        if not instance.can_be_updated_by(info.context.user):
            return UpdateEntry(errors=[
                CustomErrorType(field='non_field_errors', messages=['You cannot update this entry.'])
            ])
        serializer = EntrySerializer(instance=instance, data=entry, partial=True)
        if errors := mutation_is_not_valid(serializer):
            return UpdateEntry(errors=errors, ok=False)
        instance = serializer.save()
        return UpdateEntry(entry=instance, errors=None, ok=True)


class DeleteEntry(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    errors = graphene.List(CustomErrorType)
    ok = graphene.Boolean()
    entry = graphene.Field(EntryType)

    @staticmethod
    def mutate(root, info, entry):
        try:
            instance = Entry.objects.get(id=entry['id'])
        except Entry.DoesNotExist:
            return DeleteEntry(errors=[
                CustomErrorType(field='non_field_errors', messages=['Entry Does Not Exist.'])
            ])
        instance.delete()
        instance.id = entry['id']
        return DeleteEntry(entry=instance, errors=None, ok=True)


class Mutation(object):
    create_entry = CreateEntry.Field()
    update_entry = UpdateEntry.Field()
    delete_entry = DeleteEntry.Field()
