from django.utils import timezone

from apps.gidd.models import Conflict, ReleaseMetadata, StatusLog
from helix.caches import external_api_cache
from utils.factories import ClientFactory, CountryFactory, UserFactory
from utils.tests import HelixAPITestCase

CONFLICTS_URL = "/external-api/gidd/conflicts/"
DISASTERS_URL = "/external-api/gidd/disasters/"


class TestGiddIdFilter(HelixAPITestCase):
    """The public lists must accept an id filter without erroring.

    `Meta.fields = {"id": ["iexact"]}` compiled to `UPPER("id")`, which Postgres has no overload
    for, so any value that passed form validation reached the database and raised. It failed in
    `count()` during pagination, before serialization, and it failed regardless of how many rows
    matched -- which is why the disaster half of this test needs no fixtures.
    """

    CLIENT_CODE = "id-filter-client"

    def setUp(self):
        super().setUp()
        self.user = UserFactory.create()
        self.country = CountryFactory.create(iso3="AFG", idmc_short_name="Afghanistan")
        ReleaseMetadata.objects.create(release_year=2024, pre_release_year=2025, modified_by=self.user)
        StatusLog.objects.create(
            triggered_by=self.user,
            triggered_at=timezone.now(),
            completed_at=timezone.now(),
            status=StatusLog.Status.SUCCESS,
        )
        ClientFactory.create(code=self.CLIENT_CODE, is_active=True)
        external_api_cache.set("client_ids", [self.CLIENT_CODE], None)
        # Year under the release ceiling, or the filterset drops the rows and the test proves nothing.
        self.wanted = Conflict.objects.create(
            country=self.country, iso3="AFG", country_name="Afghanistan", year=2020, new_displacement=100
        )
        self.other = Conflict.objects.create(
            country=self.country, iso3="AFG", country_name="Afghanistan", year=2021, new_displacement=200
        )

    def tearDown(self):
        external_api_cache.delete("client_ids")
        super().tearDown()

    def test_conflicts_id_filter_selects_one_row(self):
        response = self.client.get(CONFLICTS_URL, {"client_id": self.CLIENT_CODE, "id": self.wanted.id})
        self.assertEqual(response.status_code, 200, response.content[:300])
        results = response.json()["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["year"], 2020)

    def test_conflicts_unfiltered_still_returns_both(self):
        # Guards the assertion above: one row must mean the filter worked, not that only one exists.
        response = self.client.get(CONFLICTS_URL, {"client_id": self.CLIENT_CODE})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 2)

    def test_the_old_iexact_spelling_no_longer_errors(self):
        # The exact request that used to 500. It is now an unrecognised param and is ignored, so a
        # 200 with the full set is the fix: the failure was at SQL compile time, not value-dependent.
        response = self.client.get(CONFLICTS_URL, {"client_id": self.CLIENT_CODE, "id__iexact": 0})
        self.assertEqual(response.status_code, 200, response.content[:300])
        self.assertEqual(response.json()["count"], 2)

    def test_disasters_list_is_unaffected(self):
        # RestDisasterFilterSet declares no id lookup, so this endpoint never had the defect.
        response = self.client.get(DISASTERS_URL, {"client_id": self.CLIENT_CODE})
        self.assertEqual(response.status_code, 200, response.content[:300])
