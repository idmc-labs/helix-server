from rest_framework.pagination import LimitOffsetPagination

from .models import StatusLog


class GiddLimitOffsetPagination(LimitOffsetPagination):

    def get_paginated_response(self, data):
        paginated_response = super().get_paginated_response(data)
        response_data = paginated_response.data
        response_data['last_updated'] = StatusLog.last_release_date(format="%Y-%m-%d")
        response_data.move_to_end('last_updated', last=False)
        return paginated_response

    def get_paginated_response_schema(self, schema):
        schema = super().get_paginated_response_schema(schema)
        schema['properties'] = {
            'last_updated': {
                'type': 'date',
                'example': '2024-05-13',
                'nullable': True,
            },
            **schema['properties'],
        }
        return schema
