import factory
from dateutil.utils import today
from factory.django import DjangoModelFactory

from apps.contact.models import Contact
from apps.crisis.models import Crisis
from apps.entry.models import Figure


class UserFactory(DjangoModelFactory):
    class Meta:
        model = 'users.User'

    email = factory.Sequence(lambda n: f'admin{n}@email.com')
    username = factory.Sequence(lambda n: f'username{n}')


class CountryRegionFactory(DjangoModelFactory):
    class Meta:
        model = 'country.CountryRegion'

    name = factory.Faker('first_name')


class CountryFactory(DjangoModelFactory):
    class Meta:
        model = 'country.Country'

    name = factory.Faker('first_name')
    region = factory.SubFactory(CountryRegionFactory)


class ContextualUpdateFactory(DjangoModelFactory):
    class Meta:
        model = 'country.ContextualUpdate'

    update = factory.Faker('paragraph')
    country = factory.SubFactory(CountryFactory)


class SummaryFactory(DjangoModelFactory):
    class Meta:
        model = 'country.Summary'

    summary = factory.Faker('paragraph')
    country = factory.SubFactory(CountryFactory)


class OrganizationKindFactory(DjangoModelFactory):
    class Meta:
        model = 'organization.OrganizationKind'

    title = factory.Faker('company_suffix')


class OrganizationFactory(DjangoModelFactory):
    class Meta:
        model = 'organization.Organization'


class ContactFactory(DjangoModelFactory):
    class Meta:
        model = 'contact.Contact'

    designation = factory.Iterator(Contact.DESIGNATION)
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    gender = factory.Iterator(Contact.GENDER)
    job_title = factory.Faker('job')
    organization = factory.SubFactory(OrganizationFactory)


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


class EventFactory(DjangoModelFactory):
    class Meta:
        model = 'event.Event'

    crisis = factory.SubFactory(CrisisFactory)
    event_type = factory.Iterator(Crisis.CRISIS_TYPE)


class EntryFactory(DjangoModelFactory):
    class Meta:
        model = 'entry.Entry'

    article_title = factory.Sequence(lambda n: f'long title {n}')
    source = factory.Faker('company')
    publisher = factory.Faker('company')
    publish_date = factory.LazyFunction(today().date)
    source_breakdown = factory.Sequence(lambda n: f'long text breakdown {n}')
    event = factory.SubFactory(EventFactory)
    tags = factory.Sequence(lambda n: [f'tag{each}' for each in range(n % 10)])


class FigureFactory(DjangoModelFactory):
    class Meta:
        model = 'entry.Figure'

    entry = factory.SubFactory(EntryFactory)
    district = factory.Faker('city')
    town = factory.Faker('city')
    quantifier = factory.Iterator(Figure.QUANTIFIER)
    reported = factory.Sequence(lambda n: n + 2)
    unit = factory.Iterator(Figure.UNIT)
    term = factory.Iterator(Figure.TERM)
    type = factory.Iterator(Figure.TYPE)
    role = factory.Iterator(Figure.ROLE)
    start_date = factory.LazyFunction(today().date)
    include_idu = False
