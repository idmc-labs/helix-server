import graphene
import graphene_django
from graphene_django.rest_framework.mutation import fields_for_serializer
from graphene_django.rest_framework.serializer_converter import (
    get_graphene_type_from_serializer_field,
    convert_serializer_field,
)
from rest_framework import serializers

from apps.contrib.enums import ENUM_TO_GRAPHENE_ENUM_MAP


@get_graphene_type_from_serializer_field.register(serializers.ListSerializer)
def convert_list_serializer_to_field(field):
    child_type = get_graphene_type_from_serializer_field(field.child)
    return (graphene.List, graphene.NonNull(child_type))


@get_graphene_type_from_serializer_field.register(serializers.ManyRelatedField)
def convert_serializer_field_to_id(field):
    return (graphene.List, graphene.NonNull(graphene.ID))


@get_graphene_type_from_serializer_field.register(serializers.PrimaryKeyRelatedField)
def convert_serializer_field_to_id(field):
    return graphene.ID


@get_graphene_type_from_serializer_field.register(serializers.ChoiceField)
def convert_serializer_field_to_enum(field):
    enum_type = type(list(field.choices.values())[-1])
    return ENUM_TO_GRAPHENE_ENUM_MAP.get(enum_type.__name__, graphene.String)


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
    ret_type = type(
        ref_name,
        (graphene.InputObjectType,),
        items,
    )
    convert_serializer_to_input_type.cache[serializer_class.__name__] = ret_type
    return ret_type


convert_serializer_to_input_type.cache = {}

# override the default implementation
graphene_django.rest_framework.serializer_converter.convert_serializer_to_input_type = convert_serializer_to_input_type


def generate_input_type_for_serializer(
    name: str,
    serializer_class,
) -> graphene.InputObjectType:
    data_members = fields_for_serializer(
        serializer_class(),
        only_fields=[],
        exclude_fields=[],
        is_input=True
    )
    return type(name, (graphene.InputObjectType,), data_members)