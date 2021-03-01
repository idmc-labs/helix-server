from apps.users.enums import USER_ROLE
from utils.tests import HelixGraphQLTestCase, create_user_with_role
from utils.factories import (
    CountryFactory,
    CountryRegionFactory,
    CrisisFactory,
    EventFactory,
    EntryFactory,
    TagFactory,
    FigureFactory,
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
        self.fig1entry2 = FigureFactory.create(entry=self.entry2ev1,
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

    def test_valid_extract_create_and_filter(self):
        reviewer = create_user_with_role(USER_ROLE.MONITORING_EXPERT_REVIEWER.name)
        self.force_login(reviewer)
        _input = dict(
            name='LOl',
            eventRegions=[str(self.reg1.id)]
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
