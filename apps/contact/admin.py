from django.contrib import admin

from apps.contact.models import Contact, Communication

admin.site.register(Contact)
admin.site.register(Communication)
