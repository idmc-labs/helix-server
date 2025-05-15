from django.contrib import admin

from apps.contact.models import Communication, CommunicationMedium, Contact

admin.site.register(Contact)
admin.site.register(Communication)
admin.site.register(CommunicationMedium)
