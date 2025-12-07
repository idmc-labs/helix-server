from apps.resource.models import Resource, ResourceGroup
from utils.filters import MultiWordSearchFilterSet, StringListFilter


class ResourceFilter(MultiWordSearchFilterSet):
    countries = StringListFilter(method="filter_countries")

    class Meta:
        model = Resource
        fields = {}

    @property
    def searchable_fields(self):
        return ["name"]

    @property
    def qs(self):
        if self.request.user.is_authenticated:
            return super().qs.filter(created_by=self.request.user)
        return Resource.objects.none()

    def filter_countries(self, qs, name, value):
        if not value:
            return qs
        return qs.filter(countries__in=value).distinct()


class ResourceGroupFilter(MultiWordSearchFilterSet):
    class Meta:
        model = ResourceGroup
        fields = {}

    @property
    def searchable_fields(self):
        return ["name"]

    @property
    def qs(self):
        if self.request.user.is_authenticated:
            return super().qs.filter(created_by=self.request.user)
        return ResourceGroup.objects.none()
