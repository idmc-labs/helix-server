from typing import List, Union

import graphene
from graphene import ObjectType
from graphene_django.utils.utils import _camelize_django_str


class ArrayNestedErrorType(ObjectType):
    key = graphene.String(required=True)
    object_errors = graphene.List("utils.error_types.CustomErrorType")


class CustomErrorType(ObjectType):
    field = graphene.String(required=True)
    messages = graphene.String(required=False)
    object_errors = graphene.List("utils.error_types.CustomErrorType")
    array_errors = graphene.List(ArrayNestedErrorType)


def serializer_error_to_error_types(errors: dict, initial_data: dict = None) -> List:
    initial_data = initial_data or dict()
    error_types = list()
    for field, value in errors.items():
        if isinstance(value, dict):
            error_types.append(CustomErrorType(
                field=_camelize_django_str(field),
                object_errors=serializer_error_to_error_types(value)
            ))
        elif isinstance(value, list):
            if isinstance(value[0], str):
                error_types.append(CustomErrorType(
                    field=_camelize_django_str(field),
                    messages=''.join(str(msg) for msg in value)
                ))
            elif isinstance(value[0], dict):
                array_errors = []
                for pos, array_item in enumerate(value):
                    if not array_item:
                        # array item might not have error
                        continue
                    # fetch array.item.uuid from the initial data
                    key = initial_data[field][pos].get('uuid', f'NOT_FOUND_{pos}')
                    array_errors.append(ArrayNestedErrorType(
                        key=key,
                        object_errors=serializer_error_to_error_types(array_item, initial_data[field][pos])
                    ))
                error_types.append(CustomErrorType(
                    field=_camelize_django_str(field),
                    array_errors=array_errors
                ))
        else:
            # fallback
            error_types.append(CustomErrorType(
                field=_camelize_django_str(field),
                messages=''.join(str(msg) for msg in value)
            ))
    return error_types


def mutation_is_not_valid(serializer) -> List[CustomErrorType]:
    """
    Checks if serializer is valid, if not returns list of errorTypes
    """
    if not serializer.is_valid():
        return serializer_error_to_error_types(serializer.errors, serializer.initial_data)
    return []
