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
        if self.request.user.is_authenticated:
            return super().qs.filter(created_by=self.request.user)
        return Resource.objects.none()


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
