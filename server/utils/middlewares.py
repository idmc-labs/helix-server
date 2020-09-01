APP_TO_CHECK_AGAINST = ['contact']


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
