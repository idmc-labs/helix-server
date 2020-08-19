from factory.django import DjangoModelFactory


class CountryFactory(DjangoModelFactory):
    class Meta:
        model = 'country.Country'


class OrganizationFactory(DjangoModelFactory):
    class Meta:
        model = 'organization.Organization'
