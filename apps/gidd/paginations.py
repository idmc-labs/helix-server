from typing import OrderedDict

from django.conf import settings
from rest_framework.pagination import LimitOffsetPagination

from .models import StatusLog


class GiddLimitOffsetPagination(LimitOffsetPagination):
    @property
    def max_limit(self):
        """`LimitOffsetPagination` leaves this None, which lets one request ask for every row.

        The bound is the one the GIDD GraphQL fields already enforce, so the same data is
        paged the same way whichever surface serves it. Read from settings on each call
        rather than bound at import so it is overridable in tests.

        DRF clamps `?limit=` to this silently and still advertises `next`, so a caller asking
        for more gets a page plus a link and the full `count`, never an error.
        """
        return settings.GIDD_REST_MAX_PAGE_SIZE

    def get_paginated_response(self, data):
        paginated_response = super().get_paginated_response(data)
        response_data = paginated_response.data
        response_data["last_updated"] = StatusLog.last_release_date(format="%Y-%m-%d")

        if isinstance(response_data, OrderedDict):  # TODO: Check if response_data is OrderedDict?
            response_data.move_to_end("last_updated", last=False)
        return paginated_response

    def get_paginated_response_schema(self, schema):
        schema = super().get_paginated_response_schema(schema)
        schema["properties"] = {
            "last_updated": {
                "type": "date",
                "example": "2024-05-13",
                "nullable": True,
            },
            **schema["properties"],
        }
        return schema
