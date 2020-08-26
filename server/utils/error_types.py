from typing import List

import graphene
from graphene import ObjectType
from graphene_django.utils.utils import _camelize_django_str


class NestedErrorType(ObjectType):
    field = graphene.String(required=True)
    messages = graphene.String(required=True)


class ArrayNestedErrorType(ObjectType):
    key = graphene.String(required=True)
    object_errors = graphene.List(NestedErrorType)


class CustomErrorType(ObjectType):
    field = graphene.String(required=True)
    messages = graphene.String(required=False)
    object_errors = graphene.List(NestedErrorType)
    array_errors = graphene.List(ArrayNestedErrorType)


def mutation_is_not_valid(serializer) -> List[CustomErrorType]:
    """
    Checks if serializer is valid, if not returns list of errorTypes
    """
    if not serializer.is_valid():
        errors = []
        for key, value in serializer.errors.items():
            if isinstance(value, dict):
                object_errors = []
                for k, v in value.items():
                    object_errors.append(
                        NestedErrorType(field=_camelize_django_str(k), messages=''.join(str(msg) for msg in v))
                    )
                errors.append(CustomErrorType(field=_camelize_django_str(key), object_errors=object_errors))
            elif isinstance(value, list) and isinstance(value[0], dict):
                array_errors = []
                for position, nested_instance in enumerate(value):
                    if not nested_instance:
                        # nested instance might not have error
                        continue
                    nested_object_errors = []
                    for k, v in nested_instance.items():
                        nested_object_errors.append(NestedErrorType(
                            field=_camelize_django_str(k),
                            messages=''.join(str(msg) for msg in v)
                        ))
                    array_errors.append(ArrayNestedErrorType(
                        key=position,
                        object_errors=nested_object_errors
                    ))
                errors.append(CustomErrorType(field=_camelize_django_str(key), array_errors=array_errors))
            else:
                messages = ''.join(str(msg) for msg in value)
                errors.append(CustomErrorType(field=_camelize_django_str(key), messages=messages))
        return errors
    return []
