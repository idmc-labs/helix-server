from django.contrib import admin

from apps.contact.models import Contact, Communication, CommunicationMedium

admin.site.register(Contact)
admin.site.register(Communication)
admin.site.register(CommunicationMedium)
