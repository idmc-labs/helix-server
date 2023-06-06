from django.http import HttpResponse


class DisableIntrospectionSchemaMiddleware:
    """
    This middleware should use for production mode. This class hide the
    introspection.
    """
    def resolve(self, next, root, info, **args):
        if info.field_name == '__schema':
            return None
        return next(root, info, **args)


class HealthCheckMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path == '/health':
            return HttpResponse('ok')
        return self.get_response(request)
