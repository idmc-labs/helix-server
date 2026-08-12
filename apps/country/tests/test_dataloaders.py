import json

from apps.country.dataloaders import MonitoringSubRegionCountryCountLoader
from apps.users.enums import USER_ROLE
from utils.factories import CountryFactory, MonitoringSubRegionFactory
from utils.tests import HelixGraphQLTestCase, create_user_with_role


class TestMonitoringSubRegionCountryCountLoader(HelixGraphQLTestCase):
    """A batch's values are positional: value i belongs to keys[i], whatever order the
    underlying queryset returns its rows in and whether or not every key has a row.
    """

    def setUp(self) -> None:
        self.region_one, self.region_two, self.region_three = MonitoringSubRegionFactory.create_batch(3)
        # Distinct country counts, so a value landing on the wrong key is visible.
        CountryFactory.create_batch(1, monitoring_sub_region=self.region_one)
        CountryFactory.create_batch(2, monitoring_sub_region=self.region_two)
        CountryFactory.create_batch(3, monitoring_sub_region=self.region_three)
        self.force_login(create_user_with_role(USER_ROLE.ADMIN.name))

    def test_values_follow_key_order(self) -> None:
        # Keys in descending id order, the order monitoringSubRegionList(ordering: "-id") hands
        # the loader, while the loader's own queryset is unordered.
        keys = [self.region_three.id, self.region_two.id, self.region_one.id]
        values = MonitoringSubRegionCountryCountLoader().batch_load_fn(keys).get()
        self.assertEqual(values, [3, 2, 1])

    def test_key_without_a_row_is_zero_and_does_not_shift_the_list(self) -> None:
        missing = self.region_one.id + self.region_two.id + self.region_three.id  # no such sub-region
        keys = [self.region_one.id, missing, self.region_three.id]
        values = MonitoringSubRegionCountryCountLoader().batch_load_fn(keys).get()
        self.assertEqual(values, [1, 0, 3])

    def test_graphql_list_reports_each_sub_regions_own_count(self) -> None:
        response = self.query(
            """
            query { monitoringSubRegionList(ordering: "-id") {
              results { id countriesCount }
            } }
            """
        )
        self.assertResponseNoErrors(response)
        results = json.loads(response.content)["data"]["monitoringSubRegionList"]["results"]
        counts = {row["id"]: row["countriesCount"] for row in results}
        self.assertEqual(counts[str(self.region_one.id)], 1)
        self.assertEqual(counts[str(self.region_two.id)], 2)
        self.assertEqual(counts[str(self.region_three.id)], 3)

