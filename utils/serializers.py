import json
from django.core.serializers.json import DjangoJSONEncoder
from rest_framework import serializers


class IntegerIDField(serializers.IntegerField):
    """
    This field is created to override the graphene conversion of the integerfield
    """
    pass


class GraphqlSupportDrfSerializerJSONField(serializers.JSONField):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.encoder = self.encoder or DjangoJSONEncoder

    def to_internal_value(self, data):
        try:
            if self.binary or getattr(data, 'is_json_string', False):
                if isinstance(data, bytes):
                    data = data.decode()
                return json.loads(data, cls=self.decoder)
            else:
                data = json.loads(json.dumps(data, cls=self.encoder))
        except (TypeError, ValueError):
            self.fail('invalid')
        return data
