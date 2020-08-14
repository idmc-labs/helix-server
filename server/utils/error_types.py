import json
from typing import List

import graphene
from graphene import ObjectType


class CustomErrorType(ObjectType):
    """
    Adds is_json flag to acknowledge if there are nested errors
    """
    field = graphene.String(required=True)
    messages = graphene.List(graphene.NonNull(graphene.String), required=True)
    is_json = graphene.Boolean(required=True)


def mutation_is_not_valid(serializer) -> List:
    """
    Checks if serializer is valid, if not returns list of errorTypes
    """
    if not serializer.is_valid():
        errors = []
        for key, value in serializer.errors.items():
            messages = value
            is_json = False
            if isinstance(value[0], dict):
                messages = []
                is_json = True
                for nested_error in value:
                    messages.append(json.dumps([{n_key: ''.join([str(each) for each in n_value])}
                                                for n_key, n_value in nested_error.items()]))
            errors.append(CustomErrorType(field=key, messages=messages, is_json=is_json))
        return errors
    return []
