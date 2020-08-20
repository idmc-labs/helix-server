import factory
from factory.django import DjangoModelFactory

from apps.crisis.models import Crisis


class CountryFactory(DjangoModelFactory):
    class Meta:
        model = 'country.Country'


class OrganizationFactory(DjangoModelFactory):
    class Meta:
        model = 'organization.Organization'


class DisasterCategoryFactory(DjangoModelFactory):
    class Meta:
        model = 'event.DisasterCategory'


class ViolenceFactory(DjangoModelFactory):
    class Meta:
        model = 'event.Violence'


class CrisisFactory(DjangoModelFactory):
    class Meta:
        model = 'crisis.Crisis'

    crisis_type = factory.Iterator(Crisis.CRISIS_TYPE)
