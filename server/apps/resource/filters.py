import django_filters as df

from apps.resource.models import Resource, ResourceGroup


class ResourceFilter(df.FilterSet):
    class Meta:
        model = Resource
        fields = {
            'name': ['icontains']
        }

    @property
    def qs(self):
        return super().qs.filter(created_by=self.request.user)


class ResourceGroupFilter(df.FilterSet):
    class Meta:
        model = ResourceGroup
        fields = {
            'name': ['icontains']
        }

    @property
    def qs(self):
        return super().qs.filter(created_by=self.request.user)
