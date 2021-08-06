import json
from datetime import timedelta
from django.utils import timezone
from apps.users.enums import USER_ROLE
from apps.extraction.models import ExtractionQuery
from utils.tests import HelixGraphQLTestCase, create_user_with_role
from utils.factories import (
    CountryFactory,
    CountryRegionFactory,
    CrisisFactory,
    EventFactory,
    EntryFactory,
    TagFactory,
    FigureFactory,
    FigureCategoryFactory,
)


class TestCreateExtraction(HelixGraphQLTestCase):
    def setUp(self) -> None:
        self.reg1 = CountryRegionFactory.create()
        self.reg2 = CountryRegionFactory.create()
        self.reg3 = CountryRegionFactory.create()
        self.country1reg1 = CountryFactory.create(region=self.reg1)
        self.country2reg2 = CountryFactory.create(region=self.reg2)
        self.country3reg3 = CountryFactory.create(region=self.reg3)
        self.crisis1 = CrisisFactory.create()
        self.crisis1.countries.set([self.country1reg1, self.country2reg2])
        self.crisis2 = CrisisFactory.create()
        self.crisis2.countries.set([self.country3reg3, self.country2reg2])

        self.event1crisis1 = EventFactory.create(crisis=self.crisis1)
        self.event1crisis1.countries.set([self.country2reg2])
        self.event2crisis1 = EventFactory.create(crisis=self.crisis1)
        self.event2crisis1.countries.set([self.country1reg1])
        self.event3crisis2 = EventFactory.create(crisis=self.crisis2)
        self.event3crisis2.countries.set([self.country2reg2, self.country3reg3])

        self.tag1 = TagFactory.create()
        self.tag2 = TagFactory.create()
        self.tag3 = TagFactory.create()
        self.entry1ev1 = EntryFactory.create(event=self.event1crisis1)
        self.entry1ev1.tags.set([self.tag1, self.tag2])
        FigureFactory.create(entry=self.entry1ev1,
                             country=self.country1reg1)
        self.entry2ev1 = EntryFactory.create(event=self.event1crisis1)
        self.entry2ev1.tags.set([self.tag3])
        FigureFactory.create(entry=self.entry2ev1,
                             country=self.country1reg1)
        self.entry3ev2 = EntryFactory.create(event=self.event2crisis1)
        self.entry3ev2.tags.set([self.tag2])
        self.fig1entry3 = FigureFactory.create(entry=self.entry2ev1,
                                               country=self.country3reg3)

        self.mutation = '''
        mutation CreateExtraction($input: CreateExtractInputType!) {
          createExtraction(data: $input) {
            result {
              id
              entries {
                results {
                  id
                }
              }
            }
            ok
            errors
          }
        }
        '''
        self.get_extractions = '''
        query MyQuery {
          extractionQueryList {
            results {
              id
            }
          }
        }
        '''

    def test_valid_extract_create_and_filter(self):
        reviewer = create_user_with_role(USER_ROLE.MONITORING_EXPERT.name)
        self.force_login(reviewer)
        _input = dict(
            name='LOl',
            filterFigureRegions=[str(self.reg1.id)]
        )
        response = self.query(
            self.mutation,
            input_data=_input
        )

        content = response.json()
        self.assertResponseNoErrors(response)
        self.assertTrue(content['data']['createExtraction']['ok'], content)
        self.assertEqual(
            set([each['id'] for each in
                 content['data']['createExtraction']['result']['entries']['results']]),
            {str(self.entry1ev1.id), str(self.entry2ev1.id)}
        )

    def test_extraction_query_list_filtered_by_user(self):
        reviewer1 = create_user_with_role(USER_ROLE.MONITORING_EXPERT.name)
        reviewer2 = create_user_with_role(USER_ROLE.MONITORING_EXPERT.name)
        ExtractionQuery.objects.create(name='one', created_by=reviewer1)
        ExtractionQuery.objects.create(name='one', created_by=reviewer2)
        self.force_login(reviewer1)
        response = self.query(
            self.get_extractions,
        )
        content = response.json()
        self.assertResponseNoErrors(response)
        self.assertEqual(
            len(content['data']['extractionQueryList']['results']),
            ExtractionQuery.objects.filter(created_by=reviewer1).count()
        )
        self.force_login(reviewer2)
        response = self.query(
            self.get_extractions,
        )
        content = response.json()
        self.assertResponseNoErrors(response)
        self.assertEqual(
            len(content['data']['extractionQueryList']['results']),
            ExtractionQuery.objects.filter(created_by=reviewer2).count()
        )


class TestExtractionFigureList(HelixGraphQLTestCase):
    def setUp(self) -> None:
        admin = create_user_with_role(USER_ROLE.ADMIN.name)
        for i in range(3):
            start_date = (timezone.now() - timedelta(days=30)).strftime('%Y-%m-%d')
            end_date = (timezone.now() + timedelta(days=30)).strftime('%Y-%m-%d')
            event = EventFactory.create(start_date=start_date, end_date=end_date)
            entry = EntryFactory.create(created_by=admin, event=event)
            figure_category = FigureCategoryFactory.create(type='STOCK')
            FigureFactory.create(entry=entry, created_by=admin, category=figure_category)

        self.figure_query = '''
        query MyQuery {
          extractionFigureList {
            results {
              createdAt
              id
              includeIdu
              isDisaggregated
              startDate
              endDate
            }
            totalCount
          }
        }
        '''
        self.force_login(admin)

    def test_should_retrieve_figures(self):
        response = self.query(
            self.figure_query
        )
        content = json.loads(response.content)
        self.assertResponseNoErrors(response)
        self.assertEqual(content['data']["extractionFigureList"]["totalCount"], 3)
