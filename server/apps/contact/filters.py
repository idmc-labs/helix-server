import django_filters

from apps.contact.models import Contact


class ContactFilter(django_filters.FilterSet):
    class Meta:
        model = Contact
        fields = {
            'id': ['exact'],
            'name': ['icontains'],
        }

    # @property
    # def qs(self):
    #     queryset = super().qs
    #     # lets just return queryset with objects IDs is divisible by user's id
    #     if self.request.user.id:
    #         return queryset.annotate(remainder=F('id') % self.request.user.id).filter(remainder=0)
    #     else:
    #         return queryset.none()
