import factory
from dateutil.utils import today
from factory.django import DjangoModelFactory

from apps.contact.models import Contact
from apps.crisis.models import Crisis
from apps.entry.models import Figure
from apps.entry.constants import STOCK, FLOW


class UserFactory(DjangoModelFactory):
    class Meta:
        model = 'users.User'

    email = factory.Sequence(lambda n: f'admin{n}@email.com')
    username = factory.Sequence(lambda n: f'username{n}')


class GeographicalGroupFactory(DjangoModelFactory):
    class Meta:
        model = 'country.GeographicalGroup'

    name = factory.Faker('first_name')


class CountryRegionFactory(DjangoModelFactory):
    class Meta:
        model = 'country.CountryRegion'

    name = factory.Faker('first_name')


class CountryFactory(DjangoModelFactory):
    class Meta:
        model = 'country.Country'

    name = factory.Faker('first_name')
    region = factory.SubFactory(CountryRegionFactory)


class ContextualAnalysisFactory(DjangoModelFactory):
    class Meta:
        model = 'country.ContextualAnalysis'

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

    name = factory.Faker('company_suffix')


class OrganizationFactory(DjangoModelFactory):
    class Meta:
        model = 'organization.Organization'

    short_name = factory.Sequence(lambda n: 'shortname %d' % n)


class ContactFactory(DjangoModelFactory):
    class Meta:
        model = 'contact.Contact'

    designation = factory.Iterator(Contact.DESIGNATION)
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    gender = factory.Iterator(Contact.GENDER)
    job_title = factory.Faker('job')
    organization = factory.SubFactory(OrganizationFactory)


class CommunicationMediumFactory(DjangoModelFactory):
    class Meta:
        model = 'contact.CommunicationMedium'

    name = factory.Sequence(lambda n: f'Medium{n}')


class CommunicationFactory(DjangoModelFactory):
    class Meta:
        model = 'contact.Communication'

    contact = factory.SubFactory(ContactFactory)
    title = factory.Faker('sentence')
    subject = factory.Faker('sentence')
    content = factory.Faker('paragraph')
    date_time = factory.Faker('date_time_this_month')
    medium = factory.SubFactory(CommunicationMediumFactory)


class DisasterCategoryFactory(DjangoModelFactory):
    class Meta:
        model = 'event.DisasterCategory'


class DisasterSubCategoryFactory(DjangoModelFactory):
    class Meta:
        model = 'event.DisasterSubCategory'

    category = factory.SubFactory(DisasterCategoryFactory)


class DisasterTypeFactory(DjangoModelFactory):
    class Meta:
        model = 'event.DisasterType'

    disaster_sub_category = factory.SubFactory(DisasterSubCategoryFactory)


class DisasterSubTypeFactory(DjangoModelFactory):
    class Meta:
        model = 'event.DisasterSubType'

    type = factory.SubFactory(DisasterTypeFactory)


class ViolenceFactory(DjangoModelFactory):
    class Meta:
        model = 'event.Violence'


class ViolenceSubTypeFactory(DjangoModelFactory):
    class Meta:
        model = 'event.ViolenceSubType'

    violence = factory.SubFactory(ViolenceFactory)


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
    url = 'https://www.example.com'
    publish_date = factory.LazyFunction(today().date)
    event = factory.SubFactory(EventFactory)


class FigureCategoryFactory(DjangoModelFactory):
    class Meta:
        model = 'entry.FigureCategory'

    type = factory.Iterator([STOCK, FLOW])


class FigureFactory(DjangoModelFactory):
    class Meta:
        model = 'entry.Figure'

    entry = factory.SubFactory(EntryFactory)
    country = factory.SubFactory(CountryFactory)
    category = factory.SubFactory(FigureCategoryFactory)
    quantifier = factory.Iterator(Figure.QUANTIFIER)
    reported = factory.Sequence(lambda n: n + 2)
    unit = factory.Iterator(Figure.UNIT)
    household_size = 1  # validation based on unit in the serializer
    role = factory.Iterator(Figure.ROLE)
    start_date = factory.LazyFunction(today().date)
    include_idu = False


class ResourceGroupFactory(DjangoModelFactory):
    class Meta:
        model = 'resource.ResourceGroup'

    name = factory.Sequence(lambda n: f'resource{n}')


class ResourceFactory(DjangoModelFactory):
    class Meta:
        model = 'resource.Resource'

    name = factory.Sequence(lambda n: f'resource{n}')
    group = factory.SubFactory(ResourceGroupFactory)


class ReviewCommentFactory(DjangoModelFactory):
    class Meta:
        model = 'review.ReviewComment'

    entry = factory.SubFactory(EntryFactory)


class ReviewFactory(DjangoModelFactory):
    class Meta:
        model = 'review.Review'

    entry = factory.SubFactory(EntryFactory)
    comment = factory.SubFactory(ReviewCommentFactory)


class TagFactory(DjangoModelFactory):
    class Meta:
        model = 'entry.FigureTag'


class ParkingLotFactory(DjangoModelFactory):
    class Meta:
        model = 'parking_lot.ParkedItem'

    country = factory.SubFactory(CountryFactory)


class ReportFactory(DjangoModelFactory):
    class Meta:
        model = 'report.Report'


class ReportCommentFactory(DjangoModelFactory):
    class Meta:
        model = 'report.ReportComment'

    report = factory.SubFactory(ReportFactory)
