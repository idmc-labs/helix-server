from django.contrib import admin

from apps.organization.models import Organization, OrganizationKind, SourceType

admin.site.register(Organization)
admin.site.register(OrganizationKind)
admin.site.register(SourceType)
