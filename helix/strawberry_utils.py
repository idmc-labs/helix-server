from strawberry.django.views import AsyncGraphQLView
from starlette.requests import Request
from starlette.responses import Response
from typing import Any, Optional


class CustomAsyncGraphQLView(AsyncGraphQLView):
    async def get_context(self, request: Request, response: Optional[Response]) -> Any:
        return {
            'request': request,
        }
