from django.contrib import admin

from apps.resource.models import Resource, ResourceGroup

admin.site.register(Resource)
admin.site.register(ResourceGroup)
