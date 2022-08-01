from django.conf import settings
from django.core.cache import caches


class BaseCacheProxy:
    """
    Proxy access to the default Cache object's attributes.
    This allows the legacy `cache` object to be thread-safe using the new
    ``caches`` API.
    """
    API_CACHE_ALIAS = None

    def __getattr__(self, name):
        return getattr(caches[self.API_CACHE_ALIAS], name)

    def __setattr__(self, name, value):
        return setattr(caches[self.API_CACHE_ALIAS], name, value)

    def __delattr__(self, name):
        return delattr(caches[self.API_CACHE_ALIAS], name)

    def __contains__(self, key):
        return key in caches[self.API_CACHE_ALIAS]

    def __eq__(self, other):
        return caches[self.API_CACHE_ALIAS] == other


class ExternalApiCacheProxy(BaseCacheProxy):
    API_CACHE_ALIAS = settings.EXTERNAL_API_CACHE_ALIAS


external_api_cache = ExternalApiCacheProxy()
