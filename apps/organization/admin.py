from django.contrib import admin

from apps.organization.models import Organization, OrganizationKind

admin.site.register(Organization)
admin.site.register(OrganizationKind)
