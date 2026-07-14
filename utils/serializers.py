import json

from django.core.serializers.json import DjangoJSONEncoder
from rest_framework import serializers


class IntegerIDField(serializers.IntegerField):
    """
    This field is created to override the graphene conversion of the integerfield
    """

    pass


def make_flat_to_representation(serializer: serializers.Serializer):
    """Fast path for a read-only serializer fed flat `.values()`-style dicts:
    same fields, same per-field coercions, without DRF's per-row
    bind/get_attribute machinery.
    """
    spec = [(field.field_name, field.source, field.to_representation) for field in serializer.fields.values()]
    unsupported = [source for _, source, _ in spec if "." in source]
    if unsupported:
        raise ValueError(f"dotted sources need DRF's get_attribute traversal: {unsupported}")

    def to_representation(row: dict) -> dict:
        return {name: to_repr(row[source]) if row[source] is not None else None for name, source, to_repr in spec}

    return to_representation


class GraphqlSupportDrfSerializerJSONField(serializers.JSONField):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.encoder = self.encoder or DjangoJSONEncoder

    def to_internal_value(self, data):
        try:
            if self.binary or getattr(data, "is_json_string", False):
                if isinstance(data, bytes):
                    data = data.decode()
                return json.loads(data, cls=self.decoder)
            else:
                data = json.loads(json.dumps(data, cls=self.encoder))
        except (TypeError, ValueError):
            self.fail("invalid")
        return data
