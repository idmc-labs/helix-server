from admin_auto_filters.filters import AutocompleteFilterFactory
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from apps.users.models import Portfolio, User


@admin.register(Portfolio)
class PortfolioAdmin(admin.ModelAdmin):
    list_display = ("user", "role")
    list_filter = (
        AutocompleteFilterFactory(
            "User",
            "user",
        ),
        "role",
    )


admin.site.register(User, UserAdmin)
