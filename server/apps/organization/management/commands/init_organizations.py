import requests

from django.core.management.base import BaseCommand

from apps.organization.models import OrganizationKind, Organization


class Command(BaseCommand):
    help = 'Initialize Organizations'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.org_kinds = dict()

    def fetch_organizations(self, offset=0, limit=1000):
        print('Fetching organizations starting from: {} to {}'.format(offset, offset + limit))
        URL = (
            'https://api.reliefweb.int/v1/sources?fields[include][]=logo&fields[include][]='
            'country.iso3&fields[include][]=shortname&fields[include][]=longname&fields'
            f'[include][]=homepage&fields[include][]=type&offset={offset}&limit={limit}'
        )
        response = requests.get(URL).json()

        print('Loading organizations')
        total = response.get('totalCount', 0)
        for org_data in response.get('data', []):
            self.load_organization(org_data)

        if len(response.get('data', [])) > 0:
            self.fetch_organizations(offset + limit, limit)
        print(f'Loaded {total} organizations.')

    def fetch_organization_type(self):
        print('Fetching organization types')
        URL = 'https://api.reliefweb.int/v1/references/organization-types'
        response = requests.get(URL).json()

        print('Loading organization types')
        total = len(response.get('data', []))
        for type_data in response.get('data', []):
            self.load_organization_type(type_data)
        print('{} organization types loaded.'.format(total))

    def load_organization_type(self, org_type):
        fields = org_type.get('fields')

        org_kind, _ = OrganizationKind.objects.get_or_create(
            name=fields.get('name')
        )
        self.org_kinds[org_kind.name] = org_kind.id

    def load_organization(self, org):
        fields = org['fields']
        values = dict(
            short_name=fields.get('shortName'),
            organization_kind_id=self.org_kinds.get(fields.get('type', {}).get('name', '')),
        )

        Organization.objects.update_or_create(
            name=fields['name'],
            defaults=values
        )

    def handle(self, *args, **options):
        self.fetch_organization_type()
        self.fetch_organizations()
        print(f'\nTotal {OrganizationKind.objects.count()} organization types.')
        print(f'Total {Organization.objects.count()} organizations.')
