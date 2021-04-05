import json

from debug_toolbar.middleware import DebugToolbarMiddleware as BaseMiddleware
from debug_toolbar.middleware import get_show_toolbar
from debug_toolbar.toolbar import DebugToolbar
from django.template.loader import render_to_string
from graphiql_debug_toolbar.middleware import get_payload, set_content_length
from graphiql_debug_toolbar.serializers import CallableJSONEncoder

__all__ = ['DebugToolbarMiddleware']

_HTML_TYPES = ("text/html", "application/xhtml+xml", "text/plain")


class DebugToolbarMiddleware(BaseMiddleware):
    # https://github.com/flavors/django-graphiql-debug-toolbar/issues/9
    # https://gist.github.com/ulgens/e166ad31ec71e6b1f0777a8d81ce48ae
    def __call__(self, request):
        if not get_show_toolbar()(request) or request.is_ajax():
            return self.get_response(request)

        content_type = request.content_type
        html_type = content_type in _HTML_TYPES

        if html_type:
            response = super().__call__(request)
            template = render_to_string('graphiql_debug_toolbar/base.html')
            response.write(template)
            set_content_length(response)

            return response

        toolbar = DebugToolbar(request, self.get_response)

        for panel in toolbar.enabled_panels:
            panel.enable_instrumentation()
        try:
            response = toolbar.process_request(request)
        finally:
            for panel in reversed(toolbar.enabled_panels):
                panel.disable_instrumentation()

        response = self.generate_server_timing_header(
            response,
            toolbar.enabled_panels,
        )

        try:
            payload = get_payload(request, response, toolbar)
        except:  # NOQA
            return self.get_response(request)
        response.content = json.dumps(payload, cls=CallableJSONEncoder)
        set_content_length(response)
        return response


class DisableIntrospectionSchemaMiddleware:
    """
    This middleware should use for production mode. This class hide the
    introspection.
    """
    def resolve(self, next, root, info, **args):
        if info.field_name == '__schema':
            return None
        return next(root, info, **args)
