from django.contrib import admin

from apps.entry.models import (
    Entry,
    Figure,
    FigureLocation,
    FigureTag,
)

admin.site.register(FigureTag)
admin.site.register(FigureLocation)
admin.site.register(Figure)
admin.site.register(Entry)
