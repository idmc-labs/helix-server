"""server URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
import json
from django.conf.urls.static import static
from django.contrib import admin
from django.conf import settings
from django.urls import path, re_path, include
from django.views.decorators.csrf import csrf_exempt
# from graphene_django.views import GraphQLView
from graphene_file_upload.django import FileUploadGraphQLView

from . import api_urls as rest_urls
from . import external_urls as external_rest_urls
from utils.graphene.context import GQLContext
from django_otp.admin import OTPAdminSite
from django.http import HttpRequest
from sentry_sdk.api import start_transaction


class CustomGraphQLView(FileUploadGraphQLView):
    """Handles multipart/form-data content type in django views"""
    def get_context(self, request):
        return GQLContext(request)

    def parse_body(self, request):
        """
        Allow for variable batch
        https://github.com/graphql-python/graphene-django/issues/967#issuecomment-640480919
        :param request:
        :return:
        """
        try:
            body = request.body.decode("utf-8")
            request_json = json.loads(body)
            self.batch = isinstance(request_json, list)
        except:  # noqa: E722
            self.batch = False
        return super().parse_body(request)

    def execute_graphql_request(
        self,
        request: HttpRequest,
        data,
        query,
        variables,
        operation_name,
        show_graphiql,
    ):
        operation_type = (
            self.get_backend(request)
            .document_from_string(self.schema, query)
            .get_operation_type(operation_name)
        )
        with start_transaction(op=operation_type, name=operation_name):
            return super().execute_graphql_request(
                request, data, query, variables, operation_name, show_graphiql
            )


CustomGraphQLView.graphiql_template = "graphene_graphiql_explorer/graphiql.html"

# Enable OTP in produciton
if not settings.DEBUG:
    admin.site.__class__ = OTPAdminSite

urlpatterns = [
    path('admin/', admin.site.urls),
    re_path('^graphql/?$', csrf_exempt(CustomGraphQLView.as_view())),
    path('api/', include(rest_urls)),
    path('external-api/', include(external_rest_urls))
]

if settings.DEBUG:
    import debug_toolbar
    urlpatterns = urlpatterns + [
        path('__debug__/', include(debug_toolbar.urls)),
        re_path('^graphiql/?$', csrf_exempt(CustomGraphQLView.as_view(graphiql=True))),
    ] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT) \
      + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
