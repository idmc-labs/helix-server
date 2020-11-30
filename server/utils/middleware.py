import json

from django.conf import settings
from debug_toolbar.middleware import DebugToolbarMiddleware as BaseMiddleware
from debug_toolbar.middleware import get_show_toolbar
from debug_toolbar.toolbar import DebugToolbar
from django.template.loader import render_to_string
from graphiql_debug_toolbar.middleware import get_payload, set_content_length
from graphiql_debug_toolbar.serializers import CallableJSONEncoder

APP_TO_CHECK_AGAINST = ['contact']

__all__ = ['DebugToolbarMiddleware']

_HTML_TYPES = ("text/html", "application/xhtml+xml", "text/plain")


class AuthorizationMiddleware(object):
    """
    Note: Won't be used
    Every logged in user can query
    """

    def resolve(self, next, root, info, **args):
        return_type = info.return_type
        while hasattr(return_type, 'of_type'):
            return_type = return_type.of_type
        if hasattr(return_type, 'graphene_type'):
            model = getattr(getattr(return_type.graphene_type, '_meta', None), 'model', None)
            if model and model._meta.app_label in APP_TO_CHECK_AGAINST:
                if not info.context.user.has_perm(f'{model._meta.app_label}.view_{model._meta.model_name}'):
                    return None
        return next(root, info, **args)


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

        payload = get_payload(request, response, toolbar)
        response.content = json.dumps(payload, cls=CallableJSONEncoder)
        set_content_length(response)
        return response
