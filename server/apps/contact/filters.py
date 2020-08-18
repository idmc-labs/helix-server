import django_filters

from apps.contact.models import Contact


class ContactFilter(django_filters.FilterSet):
    class Meta:
        model = Contact
        fields = {
            'id': ['exact'],
            'first_name': ['icontains'],
            'last_name': ['icontains'],
        }
