import graphene
from django.utils.translation import gettext_lazy as _

from apps.entry.enums import QuantifierGrapheneEnum, RoleGrapheneEnum, TypeGrapheneEnum, \
    TermGrapheneEnum, UnitGrapheneEnum
from apps.entry.models import Entry, Figure
from apps.entry.schema import EntryType, FigureType
from apps.entry.serializers import EntrySerializer, FigureSerializer
from utils.error_types import CustomErrorType, mutation_is_not_valid
from utils.permissions import permission_checker


class CommonFigureCreateMixin:
    district = graphene.String(required=True)
    town = graphene.String(required=True)
    quantifier = graphene.NonNull(QuantifierGrapheneEnum)
    reported = graphene.Int(required=True)
    unit = graphene.NonNull(UnitGrapheneEnum)
    term = graphene.NonNull(TermGrapheneEnum)
    type = graphene.NonNull(TypeGrapheneEnum)
    role = graphene.NonNull(RoleGrapheneEnum)
    start_date = graphene.Date(required=True)
    include_idu = graphene.Boolean(required=True)
    excerpt_idu = graphene.String()


class NestedFigureCreateInputType(CommonFigureCreateMixin, graphene.InputObjectType):
    """
    Input Type used to create figures with entry
    """
    uuid = graphene.String(required=True)


class FigureCreateInputType(CommonFigureCreateMixin, graphene.InputObjectType):
    entry = graphene.ID(required=True)
    uuid = graphene.String()


class FigureUpdateInputType(graphene.InputObjectType):
    id = graphene.ID(required=True)
    uuid = graphene.String()
    entry = graphene.ID()
    district = graphene.String()
    town = graphene.String()
    quantifier = graphene.Field(QuantifierGrapheneEnum)
    reported = graphene.Int()
    unit = graphene.Field(UnitGrapheneEnum)
    term = graphene.Field(TermGrapheneEnum)
    type = graphene.Field(TypeGrapheneEnum)
    role = graphene.Field(RoleGrapheneEnum)
    start_date = graphene.Date()
    include_idu = graphene.Boolean()
    excerpt_idu = graphene.String()


class CreateFigure(graphene.Mutation):
    class Arguments:
        figure = FigureCreateInputType(required=True)

    errors = graphene.List(CustomErrorType)
    ok = graphene.Boolean()
    figure = graphene.Field(FigureType)

    @staticmethod
    @permission_checker(['entry.add_figure'])
    def mutate(root, info, figure):
        serializer = FigureSerializer(data=figure,
                                      context={'request': info.context})
        try:
            entry = Entry.objects.get(id=figure['entry'])
        except Entry.DoesNotExist:
            return CreateFigure(errors=[
                CustomErrorType(field='non_field_errors', messages=[_('Entry does not exist.')])
            ])
        if not Figure.can_be_created_by(info.context.user, entry=entry):
            return CreateFigure(errors=[
                CustomErrorType(field='non_field_errors', messages=[_('You cannot create a figure into this entry.')])
            ])
        if errors := mutation_is_not_valid(serializer):
            return CreateFigure(errors=errors, ok=False)
        instance = serializer.save()
        return CreateFigure(figure=instance, errors=None, ok=True)


class UpdateFigure(graphene.Mutation):
    class Arguments:
        figure = FigureUpdateInputType(required=True)

    errors = graphene.List(CustomErrorType)
    ok = graphene.Boolean()
    figure = graphene.Field(FigureType)

    @staticmethod
    @permission_checker(['entry.change_figure'])
    def mutate(root, info, figure):
        try:
            instance = Figure.objects.get(id=figure['id'])
        except Figure.DoesNotExist:
            return UpdateFigure(errors=[
                CustomErrorType(field='non_field_errors', messages=['Figure Does Not Exist.'])
            ])
        if not instance.can_be_updated_by(info.context.user):
            return UpdateFigure(errors=[
                CustomErrorType(field='non_field_errors', messages=[_('You cannot update this figure.')])
            ])
        serializer = FigureSerializer(instance=instance, data=figure,
                                      context={'request': info.context}, partial=True)
        if errors := mutation_is_not_valid(serializer):
            return UpdateFigure(errors=errors, ok=False)
        instance = serializer.save()
        return UpdateFigure(figure=instance, errors=None, ok=True)


class DeleteFigure(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    errors = graphene.List(CustomErrorType)
    ok = graphene.Boolean()
    figure = graphene.Field(FigureType)

    @staticmethod
    @permission_checker(['entry.delete_figure'])
    def mutate(root, info, id):
        try:
            instance = Figure.objects.get(id=id)
        except Figure.DoesNotExist:
            return DeleteFigure(errors=[
                CustomErrorType(field='non_field_errors', messages=['Figure Does Not Exist.'])
            ])
        if not instance.can_be_updated_by(info.context.user):
            return DeleteFigure(errors=[
                CustomErrorType(field='non_field_errors', messages=[_('You cannot delete this figure.')])
            ])
        instance.delete()
        instance.id = id
        return DeleteFigure(figure=instance, errors=None, ok=True)


# entry


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
    figures = graphene.List(NestedFigureCreateInputType)
    idmc_analysis = graphene.String()
    methodology = graphene.String()
    tags = graphene.List(graphene.String, required=False)
    reviewers = graphene.List(graphene.ID)


class EntryUpdateInputType(graphene.InputObjectType):
    id = graphene.ID(required=True)
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
    @permission_checker(['entry.add_entry'])
    def mutate(root, info, entry):
        serializer = EntrySerializer(data=entry, context={'request': info.context})
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
                CustomErrorType(field='non_field_errors', messages=[_('You cannot update this entry.')])
            ])
        serializer = EntrySerializer(instance=instance, data=entry,
                                     context={'request': info.context}, partial=True)
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
    @permission_checker(['entry.delete_entry'])
    def mutate(root, info, id):
        try:
            instance = Entry.objects.get(id=id)
        except Entry.DoesNotExist:
            return DeleteEntry(errors=[
                CustomErrorType(field='non_field_errors', messages=['Entry Does Not Exist.'])
            ])
        if not instance.can_be_updated_by(info.context.user):
            return DeleteEntry(errors=[
                CustomErrorType(field='non_field_errors', messages=[_('You cannot delete this entry.')])
            ])
        instance.delete()
        instance.id = id
        return DeleteEntry(entry=instance, errors=None, ok=True)


class Mutation(object):
    create_figure = CreateFigure.Field()
    update_figure = UpdateFigure.Field()
    delete_figure = DeleteFigure.Field()
    create_entry = CreateEntry.Field()
    update_entry = UpdateEntry.Field()
    delete_entry = DeleteEntry.Field()
