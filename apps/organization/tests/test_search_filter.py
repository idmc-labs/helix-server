from apps.organization.filters import OrganizationFilter
from utils.factories import CountryFactory, OrganizationFactory
from utils.tests import HelixTestCase


class TestOrganizationMultiWordSearchFilter(HelixTestCase):
    """Record-level multi-word search over a FORWARD M2M path (`countries__name`)
    — the `to_many_exists` branch that correlates through `related_query_name()`
    (CrisisFilter's tests cover the reverse-FK branch).
    """

    def setUp(self) -> None:
        self.filter_class = OrganizationFilter

    def test_record_level_truth_table_over_m2m(self):
        org = OrganizationFactory.create(name="Himalayan Relief", short_name="HRO")
        org.countries.set([CountryFactory.create(name="Nepal"), CountryFactory.create(name="Bhutan")])

        # Control: shares one country but nothing else.
        other = OrganizationFactory.create(name="Coastal Aid", short_name="CAO")
        other.countries.set([CountryFactory.create(name="India")])

        matching_searches = [
            "himalayan",
            "relief",
            "hro",  # short_name
            "nepal",
            "bhutan",
            "himalayan nepal",  # parent + child
            "nepal bhutan",  # two DIFFERENT country rows (record-level)
            "relief nepal bhutan",
        ]
        non_matching_searches = [
            "gandaki",
            "himalayan india",  # terms split across DIFFERENT organizations
            "nepal india",
        ]
        for search in matching_searches:
            with self.subTest(search=search, expected="match"):
                self.assertQuerySetEqual([org], self.filter_class(data=dict(search=search)).qs)
        for search in non_matching_searches:
            with self.subTest(search=search, expected="no match"):
                self.assertQuerySetEqual([], self.filter_class(data=dict(search=search)).qs)
        # The control org is reachable through ITS OWN country.
        self.assertQuerySetEqual([other], self.filter_class(data=dict(search="india")).qs)
