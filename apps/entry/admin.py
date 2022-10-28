from django.contrib import admin

from apps.entry.models import (
    FigureTag,
    OSMName,
    Figure,
    Entry,
)

admin.site.register(FigureTag)
admin.site.register(OSMName)
admin.site.register(Figure)
admin.site.register(Entry)
