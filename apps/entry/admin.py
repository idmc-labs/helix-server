from django.contrib import admin

from apps.entry.models import (
    FigureTag,
    OSMName,
    Figure,
    Entry,
    EntryReviewer,
)

admin.site.register(FigureTag)
admin.site.register(OSMName)
admin.site.register(Figure)
admin.site.register(Entry)
admin.site.register(EntryReviewer)
