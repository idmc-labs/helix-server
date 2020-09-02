import django_filters

from apps.crisis.models import Crisis


class CrisisFilter(django_filters.FilterSet):
    class Meta:
        model = Crisis
        fields = {
            'countries': ['exact'],
            'name': ['icontains']
        }
