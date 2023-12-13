from django.contrib import admin

from apps.event.models import Event, Violence, \
    ViolenceSubType, Actor, DisasterCategory, DisasterSubCategory, DisasterType, \
    DisasterSubType, EventCode

admin.site.register(Event)
admin.site.register(Violence)
admin.site.register(ViolenceSubType)
admin.site.register(Actor)
admin.site.register(DisasterType)
admin.site.register(DisasterSubType)
admin.site.register(DisasterCategory)
admin.site.register(DisasterSubCategory)
admin.site.register(EventCode)
