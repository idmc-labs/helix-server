from factory.django import DjangoModelFactory


class OrganizationFactory(DjangoModelFactory):
    class Meta:
        model = 'organization.Organization'
