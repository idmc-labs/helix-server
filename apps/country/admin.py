from admin_auto_filters.filters import AutocompleteFilterFactory
from django.contrib import admin

from apps.country.models import (
    ContextualAnalysis,
    Country,
    CountryRegion,
    GeographicalGroup,
    HouseholdSize,
    Summary,
)


@admin.register(HouseholdSize)
class HouseholdSizeAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "country",
        "year",
        "size",
    )
    list_filter = (
        AutocompleteFilterFactory("Country", "country"),
        "year",
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("country")


admin.site.register(GeographicalGroup)
admin.site.register(CountryRegion)
admin.site.register(ContextualAnalysis)
admin.site.register(Summary)
admin.site.register(Country)
