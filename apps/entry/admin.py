from django.contrib import admin

from apps.entry.models import (
    FigureTag,
    FigureLocation,
    Figure,
    Entry,
)

admin.site.register(FigureTag)
admin.site.register(FigureLocation)
admin.site.register(Figure)
admin.site.register(Entry)
