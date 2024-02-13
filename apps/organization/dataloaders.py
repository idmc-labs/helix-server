from collections import defaultdict

from promise import Promise
from promise.dataloader import DataLoader

from .models import Organization


class OrganizationCountriesLoader(DataLoader):
    def batch_load_fn(self, keys: list):
        qs = Organization.countries.through.objects.filter(organization__in=keys).select_related('country').only(
            'organization_id',
            'country',
        )
        _map = defaultdict(list)
        for organization in qs:
            _map[organization.organization_id].append(organization.country)
        return Promise.resolve([_map.get(key) for key in keys])


class OrganizationOrganizationKindLoader(DataLoader):
    def batch_load_fn(self, keys: list):
        qs = Organization.objects.filter(id__in=keys).select_related('organization_kind').only(
            'id',
            'organization_kind',
        )
        _map = {}
        for organization in qs.all():
            _map[organization.id] = organization.organization_kind
        return Promise.resolve([_map.get(key) for key in keys])
