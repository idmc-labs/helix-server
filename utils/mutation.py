import typing
from collections import OrderedDict

import inspect
import graphene
import graphene_django
from graphene.types.generic import GenericScalar
from graphene_django.registry import get_global_registry
from graphene_django.rest_framework.serializer_converter import (
    get_graphene_type_from_serializer_field,
)
from rest_framework import serializers
from django.conf import settings
from django.db import models, transaction
from django.core.exceptions import PermissionDenied
from django.utils.translation import gettext

from utils.serializers import IntegerIDField
from apps.contrib.enums import ENUM_TO_GRAPHENE_ENUM_MAP
from utils.error_types import mutation_is_not_valid
from utils.permissions import PERMISSION_DENIED_MESSAGE


@get_graphene_type_from_serializer_field.register(serializers.ListSerializer)
def convert_list_serializer_to_field(field):
    child_type = get_graphene_type_from_serializer_field(field.child)
    return (graphene.List, graphene.NonNull(child_type))


@get_graphene_type_from_serializer_field.register(serializers.ListField)
def convert_list_field_to_field(field):
    child_type = get_graphene_type_from_serializer_field(field.child)
    return (graphene.List, graphene.NonNull(child_type))


@get_graphene_type_from_serializer_field.register(serializers.Serializer)
def convert_serializer_to_field(field):
    return graphene.Field


@get_graphene_type_from_serializer_field.register(serializers.ManyRelatedField)
def convert_serializer_field_to_many_related_id(field):
    return (graphene.List, graphene.NonNull(graphene.ID))


@get_graphene_type_from_serializer_field.register(serializers.PrimaryKeyRelatedField)
@get_graphene_type_from_serializer_field.register(IntegerIDField)
def convert_serializer_field_to_id(field):
    return graphene.ID


# TODO: This need to be done object type level as well
# @get_graphene_type_from_serializer_field.register(serializers.JSONField)
# @get_graphene_type_from_serializer_field.register(serializers.DictField)
# def convert_serializer_field_to_generic_scalar(field):
#     return GenericScalar


@get_graphene_type_from_serializer_field.register(serializers.ChoiceField)
def convert_serializer_field_to_enum(field):
    enum_type = type(list(field.choices.values())[-1])
    return ENUM_TO_GRAPHENE_ENUM_MAP.get(enum_type.__name__, graphene.String)


def convert_serializer_field(field, is_input=True, convert_choices_to_enum=True, force_optional=False):
    """
    Converts a django rest frameworks field to a graphql field
    and marks the field as required if we are creating an input type
    and the field itself is required
    """

    if isinstance(field, serializers.ChoiceField) and not convert_choices_to_enum:
        graphql_type = graphene.String
    else:
        graphql_type = get_graphene_type_from_serializer_field(field)

    args = []
    kwargs = {
        "description": field.help_text,
        "required": is_input and field.required and not force_optional
    }

    # if it is a tuple or a list it means that we are returning
    # the graphql type and the child type
    if isinstance(graphql_type, (list, tuple)):
        kwargs["of_type"] = graphql_type[1]
        graphql_type = graphql_type[0]

    if isinstance(field, serializers.ModelSerializer):
        if is_input:
            graphql_type = convert_serializer_to_input_type(field.__class__)
        else:
            global_registry = get_global_registry()
            field_model = field.Meta.model
            args = [global_registry.get_type_for_model(field_model)]
    elif isinstance(field, serializers.Serializer):
        if is_input:
            graphql_type = convert_serializer_to_input_type(field.__class__)
    elif isinstance(field, serializers.ListSerializer):
        field = field.child
        if is_input:
            # All the serializer items within the list is considered non-nullable
            kwargs["of_type"] = graphene.NonNull(convert_serializer_to_input_type(field.__class__))
        else:
            del kwargs["of_type"]
            global_registry = get_global_registry()
            field_model = field.Meta.model
            args = [global_registry.get_type_for_model(field_model)]

    return graphql_type(*args, **kwargs)


def convert_serializer_to_input_type(serializer_class):
    """
    graphene_django.rest_framework.serializer_converter.convert_serializer_to_input_type
    """
    cached_type = convert_serializer_to_input_type.cache.get(
        serializer_class.__name__, None
    )
    if cached_type:
        return cached_type
    serializer = serializer_class()

    items = {
        name: convert_serializer_field(field)
        for name, field in serializer.fields.items()
    }
    # Alter naming
    serializer_name = serializer.__class__.__name__
    serializer_name = ''.join(''.join(serializer_name.split('ModelSerializer')).split('Serializer'))
    ref_name = f'{serializer_name}InputType'

    base_classes = (graphene.InputObjectType,)

    ret_type = type(
        ref_name,
        base_classes,
        items,
    )
    convert_serializer_to_input_type.cache[serializer_class.__name__] = ret_type
    return ret_type


convert_serializer_to_input_type.cache = {}


def fields_for_serializer(
    serializer,
    only_fields,
    exclude_fields,
    is_input=False,
    convert_choices_to_enum=True,
    lookup_field=None,
    partial=False,
):
    """
    NOTE: Same as the original definition. Needs overriding to
    handle relative import of convert_serializer_field
    """
    fields = OrderedDict()
    for name, field in serializer.fields.items():
        is_not_in_only = only_fields and name not in only_fields
        is_excluded = any(
            [
                name in exclude_fields,
                field.write_only and
                not is_input,  # don't show write_only fields in Query
                field.read_only and is_input \
                and lookup_field != name,  # don't show read_only fields in Input
            ]
        )

        if is_not_in_only or is_excluded:
            continue

        fields[name] = convert_serializer_field(
            field,
            is_input=is_input,
            convert_choices_to_enum=convert_choices_to_enum,
            force_optional=partial,
        )
    return fields


def generate_input_type_for_serializer(
    name: str,
    serializer_class,
    partial=False,
) -> graphene.InputObjectType:
    data_members = fields_for_serializer(
        serializer_class(),
        only_fields=[],
        exclude_fields=[],
        is_input=True,
        partial=partial,
    )
    return type(
        name,
        (graphene.InputObjectType,),
        data_members
    )


# Only use this for single object type with direct scalar access.
def generate_object_field_from_input_type(input_type, skip_fields=[]):
    new_fields_map = {}
    for field_key, field in input_type._meta.fields.items():
        if field_key in skip_fields:
            continue
        _type = field.type
        if inspect.isclass(_type) and (
            issubclass(_type, graphene.Scalar) or
            issubclass(_type, graphene.Enum)
        ):
            new_fields_map[field_key] = graphene.Field(_type)
        else:
            new_fields_map[field_key] = _type
    return new_fields_map


def compare_input_output_type_fields(input_type, output_type):
    if len(output_type._meta.fields) != len(input_type._meta.fields):
        for field in input_type._meta.fields.keys():
            if field not in output_type._meta.fields.keys():
                print('---> [Entry] Missing: ', field)
        raise Exception('Conversion failed')


# override the default implementation
graphene_django.rest_framework.serializer_converter.convert_serializer_field = convert_serializer_field
graphene_django.rest_framework.serializer_converter.convert_serializer_to_input_type = convert_serializer_to_input_type


# Custom mutations
class BulkUpdateMutation(graphene.Mutation):
    # TODO: Use proper class inheritance using template
    class Arguments:
        items = graphene.List(graphene.NonNull(graphene.InputObjectType))
        delete_ids = graphene.List(graphene.NonNull(graphene.ID))

    serializer_class: typing.Type[serializers.ModelSerializer]
    model: typing.Type[models.Model]
    errors = graphene.List(GenericScalar)
    permissions: typing.List[str]
    result = graphene.List(graphene.ObjectType)
    deleted_result = graphene.List(graphene.ObjectType)

    @staticmethod
    def get_queryset() -> models.QuerySet:
        raise Exception('Implementation required')

    @classmethod
    def get_valid_delete_items(cls, delete_ids) -> models.QuerySet:
        return cls.get_queryset().filter(pk__in=delete_ids)

    @classmethod
    def get_object(cls, id) -> typing.Tuple[typing.Optional[models.Model], typing.Optional[typing.List[typing.Any]]]:
        try:
            return cls.get_queryset().get(id=id), None
        except cls.model.DoesNotExist:
            return None, [
                dict(field='nonFieldErrors', messages=f'{cls.model.__name__} does not exist.')
            ]

    @classmethod
    @transaction.atomic
    def save_item(cls, info, item, id, context):
        if id:
            instance, errors = cls.get_object(id)
            if errors:
                return None, errors
            serializer = cls.serializer_class(
                instance=instance,
                data=item,
                context=context,
                partial=True,
            )
        else:
            serializer = cls.serializer_class(
                data=item,
                context=context,
            )
        if errors := mutation_is_not_valid(serializer):
            return None, errors
        instance = serializer.save()
        return instance, None

    @classmethod
    @transaction.atomic
    def delete_item(cls, item, context):
        old_id = item.pk
        item.delete()
        # add old id so that client can use it if required
        item.pk = old_id
        return item

    @classmethod
    def get_batch_max_size_limit(cls):
        if hasattr(cls, 'BATCH_MAX_SIZE_LIMIT'):
            return cls.BATCH_MAX_SIZE_LIMIT
        return settings.GRAPHENE_BATCH_DEFAULT_MAX_LIMIT

    @classmethod
    def validate_batch_size(cls, items, delete_ids):
        delete_items_len = 0
        items_len = 0
        if items:
            items_len = len(items)
        if delete_ids:
            delete_items_len = len(delete_ids)
        all_len = items_len + delete_items_len
        if all_len > cls.get_batch_max_size_limit():
            raise PermissionDenied(
                gettext(
                    'Max limit for batch is %(limit)s. But %(all_len)s where provided.'
                    ' Where CREATE/UPDATE = %(items_len)s and DELETE = %(delete_items_len)s'
                ) % {
                    'limit': cls.get_batch_max_size_limit(),
                    'all_len': all_len,
                    'items_len': items_len,
                    'delete_items_len': delete_items_len,
                }
            )

    @classmethod
    def mutate(cls, _, info, items=None, delete_ids=None, context=None):
        cls.validate_batch_size(items, delete_ids)

        if not info.context.user.has_perms(cls.permissions):
            raise PermissionDenied(gettext(PERMISSION_DENIED_MESSAGE))

        internal_context = {
            'request': info.context,
            **(context or {})
        }
        all_errors = []
        all_instances = []
        all_deleted_instances = []
        # Bulk Delete
        if delete_ids:
            delete_items_qs = cls.get_valid_delete_items(delete_ids)
            for item in delete_items_qs:
                all_deleted_instances.append(cls.delete_item(item, internal_context))
        # Bulk Create/Update
        for item in items or []:
            id = item.get('id')
            instance, errors = cls.save_item(info, item, id, internal_context)
            all_errors.append(errors)
            all_instances.append(instance)
        return cls(
            result=all_instances,
            errors=all_errors,
            deleted_result=all_deleted_instances,
        )
