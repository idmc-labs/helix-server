import django_filters as df

from apps.resource.models import Resource, ResourceGroup
from utils.filters import StringListFilter


class ResourceFilter(df.FilterSet):
    countries = StringListFilter(method='filter_countries')

    class Meta:
        model = Resource
        fields = {
            'name': ['icontains']
        }

    @property
    def qs(self):
        if self.request.user.is_authenticated:
            return super().qs.filter(created_by=self.request.user)
        return Resource.objects.none()

    def filter_countries(self, qs, name, value):
        if not value:
            return qs
        return qs.filter(countries__in=value).distinct()


class ResourceGroupFilter(df.FilterSet):
    class Meta:
        model = ResourceGroup
        fields = {
            'name': ['icontains']
        }

    @property
    def qs(self):
        if self.request.user.is_authenticated:
            return super().qs.filter(created_by=self.request.user)
        return ResourceGroup.objects.none()
