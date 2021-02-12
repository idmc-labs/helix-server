from django.contrib import admin

from apps.country.models import (
    GeographicalGroup,
    CountryRegion,
    ContextualAnalysis,
    Summary,
    HouseholdSize,
    Country,
)

admin.site.register(GeographicalGroup)
admin.site.register(CountryRegion)
admin.site.register(ContextualAnalysis)
admin.site.register(Summary)
admin.site.register(HouseholdSize)
admin.site.register(Country)
