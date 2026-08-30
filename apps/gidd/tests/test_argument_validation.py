"""A bad GIDD argument must come back as a readable client error, and only for the field it broke.

Every case here returned a 200 before: a wrong answer (`endYear: 2023.5`, `PRE-RELEASE`), an
unhandled exception dressed as a GraphQL error (`pageSize: -1`), or an error that emptied the whole
document because the field it failed on was non-null.
"""

import datetime

from django.test import TestCase

from apps.contrib.models import Client
from apps.crisis.models import Crisis
from apps.gidd.models import GiddDisplacement, ReleaseMetadata, StatusLog
from helix.caches import external_api_cache
from utils.factories import ClientFactory, CountryFactory, UserFactory
from utils.graphene.pagination import get_page_size
from utils.tests import HelixAPITestCase, HelixGraphQLTestCase

RELEASE_YEAR = 2023
MAX_PAGE_SIZE = 100

COUNTRY_YEARS = """
    query($clientId: String!, $pageSize: Int) {
        giddPublicCountryYearDisplacements(clientId: $clientId, pageSize: $pageSize) {
            totalCount
            page
            pageSize
            results { iso3 year }
        }
    }
"""

CONFLICT_STATISTICS = """
    query($clientId: String!, $releaseEnvironment: String, $startYear: Int, $endYear: Int) {
        giddPublicConflictStatistics(
            clientId: $clientId
            releaseEnvironment: $releaseEnvironment
            startYear: $startYear
            endYear: $endYear
        ) {
            newDisplacements
            totalDisplacements
        }
    }
"""

# `endYear` inline rather than through a variable: a fractional literal has to be rejected by the
# argument's own type, which is what a variable declaration would hide.
CONFLICT_STATISTICS_FRACTIONAL_END_YEAR = """
    query($clientId: String!) {
        giddPublicConflictStatistics(clientId: $clientId, endYear: 2023.5) {
            newDisplacements
            totalDisplacements
        }
    }
"""

STATISTICS_BESIDE_A_SIBLING = """
    query($clientId: String!) {
        giddPublicConflictStatistics(clientId: $clientId, startYear: -1) {
            newDisplacements
        }
        giddPublicCountries(clientId: $clientId) {
            iso3
        }
    }
"""


class GiddArgumentFixtureMixin:
    CLIENT_CODE = "GIDD-ARGUMENT-VALIDATION"

    @classmethod
    def seed_gidd(cls):
        Client.objects.create(name="Gidd Argument Validation", code=cls.CLIENT_CODE, is_active=True)
        ReleaseMetadata.objects.create(
            release_year=RELEASE_YEAR,
            pre_release_year=RELEASE_YEAR - 1,
            modified_by=UserFactory.create(),
        )
        country = CountryFactory.create(name="Nepal", iso3="NPL")
        GiddDisplacement.objects.create(
            country=country,
            iso3=country.iso3,
            country_name=country.name,
            year=RELEASE_YEAR,
            cause=Crisis.CRISIS_TYPE.CONFLICT,
            new_displacement=500,
            total_displacement=5000,
        )

    def errors_of(self, payload):
        return [error["message"] for error in payload.get("errors") or []]


class GiddPageSizeValidationTestCase(GiddArgumentFixtureMixin, HelixGraphQLTestCase):
    """An out-of-range `pageSize` is a client error, not an exception from the ORM."""

    @classmethod
    def setUpTestData(cls):
        cls.seed_gidd()

    def country_years(self, **variables):
        response = self.query(COUNTRY_YEARS, variables=dict(clientId=self.CLIENT_CODE, **variables))
        self.assertEqual(response.status_code, 200, response.content)
        return response.json()

    def test_absent_page_size_serves_the_default(self):
        payload = self.country_years()
        assert not payload.get("errors"), payload["errors"]
        assert payload["data"]["giddPublicCountryYearDisplacements"]["pageSize"] == 50, payload

    def test_a_page_size_within_the_bounds_is_served(self):
        payload = self.country_years(pageSize=1)
        assert not payload.get("errors"), payload["errors"]
        assert payload["data"]["giddPublicCountryYearDisplacements"]["pageSize"] == 1, payload

    def test_negative_page_size_is_refused_by_name(self):
        payload = self.country_years(pageSize=-1)
        messages = self.errors_of(payload)
        assert messages, payload
        assert any("Page size must be a positive integer" in message for message in messages), messages
        # The defect: `rows[0:-1]` raised out of query compilation, naming an ORM operation the
        # client never asked for instead of the argument it sent.
        assert not any("indexing" in message.lower() for message in messages), messages
        assert payload["data"]["giddPublicCountryYearDisplacements"] is None, payload

    def test_zero_page_size_is_refused_rather_than_read_as_the_default(self):
        payload = self.country_years(pageSize=0)
        messages = self.errors_of(payload)
        assert any("Page size must be a positive integer" in message for message in messages), messages
        assert payload["data"]["giddPublicCountryYearDisplacements"] is None, payload

    def test_page_size_beyond_the_maximum_is_refused(self):
        payload = self.country_years(pageSize=MAX_PAGE_SIZE + 1)
        messages = self.errors_of(payload)
        assert any("Max page size limit" in message for message in messages), messages


class GetPageSizeTestCase(TestCase):
    """The page-size bounds must be real exceptions: `python -O` strips an `assert` and its guard."""

    def test_the_upper_bound_raises_rather_than_asserts(self):
        with self.assertRaises(ValueError):
            get_page_size(MAX_PAGE_SIZE + 1)

    def test_a_non_positive_size_raises(self):
        with self.assertRaises(ValueError):
            get_page_size(-1)
        with self.assertRaises(ValueError):
            get_page_size(0)

    def test_an_absent_size_still_takes_the_default(self):
        assert get_page_size(None) == 20


class GiddYearArgumentValidationTestCase(GiddArgumentFixtureMixin, HelixGraphQLTestCase):
    """A GIDD year is a positive whole number, and anything else is refused rather than answered."""

    @classmethod
    def setUpTestData(cls):
        cls.seed_gidd()

    def statistics(self, query=CONFLICT_STATISTICS, **variables):
        response = self.query(query, variables=dict(clientId=self.CLIENT_CODE, **variables))
        self.assertEqual(response.status_code, 200, response.content)
        return response.json()

    def test_a_whole_year_is_still_accepted(self):
        payload = self.statistics(startYear=RELEASE_YEAR, endYear=RELEASE_YEAR)
        assert not payload.get("errors"), payload["errors"]
        assert payload["data"]["giddPublicConflictStatistics"]["totalDisplacements"] == 5000, payload

    def test_a_fractional_year_is_refused(self):
        # A literal of the wrong type fails document validation, which this view answers with a
        # 400 carrying the same `errors` shape rather than the usual 200.
        response = self.query(
            CONFLICT_STATISTICS_FRACTIONAL_END_YEAR,
            variables=dict(clientId=self.CLIENT_CODE),
        )
        self.assertEqual(response.status_code, 400, response.content)
        payload = response.json()
        messages = self.errors_of(payload)
        assert messages, payload
        # The defect: `Float` accepted 2023.5, and IDP stock -- selected by year EQUALITY --
        # came back as 0 beside a full new-displacement sum.
        assert any("Int" in message for message in messages), messages

    def test_a_negative_year_is_refused(self):
        payload = self.statistics(startYear=-1)
        messages = self.errors_of(payload)
        assert any("must be a positive year" in message for message in messages), messages

    def test_a_zero_year_is_refused(self):
        payload = self.statistics(endYear=0)
        messages = self.errors_of(payload)
        assert any("must be a positive year" in message for message in messages), messages


class GiddReleaseEnvironmentValidationTestCase(GiddArgumentFixtureMixin, HelixGraphQLTestCase):
    """An unrecognised `releaseEnvironment` must not be served as RELEASE."""

    @classmethod
    def setUpTestData(cls):
        cls.seed_gidd()

    def statistics(self, **variables):
        response = self.query(CONFLICT_STATISTICS, variables=dict(clientId=self.CLIENT_CODE, **variables))
        self.assertEqual(response.status_code, 200, response.content)
        return response.json()

    def test_a_near_miss_is_refused_rather_than_served_as_release(self):
        for value in ("PRE-RELEASE", "prerelease", "banana"):
            payload = self.statistics(releaseEnvironment=value)
            messages = self.errors_of(payload)
            assert any("Invalid release environment" in message for message in messages), (value, payload)
            assert payload["data"]["giddPublicConflictStatistics"] is None, (value, payload)

    def test_both_environments_are_still_accepted_in_either_case(self):
        for value in ("RELEASE", "release", "PRE_RELEASE", "pre_release"):
            payload = self.statistics(releaseEnvironment=value)
            assert not payload.get("errors"), (value, payload["errors"])

    def test_a_null_environment_still_defaults_to_release(self):
        # Guards the earlier fix: the fallback must survive the validation added around it.
        payload = self.statistics(releaseEnvironment=None)
        assert not payload.get("errors"), payload["errors"]
        assert payload["data"]["giddPublicConflictStatistics"]["newDisplacements"] == 500, payload


class GiddStatisticsNullabilityTestCase(GiddArgumentFixtureMixin, HelixGraphQLTestCase):
    """An error on one statistics field must not empty its siblings."""

    @classmethod
    def setUpTestData(cls):
        cls.seed_gidd()

    def test_a_bad_argument_leaves_the_sibling_fields_standing(self):
        response = self.query(STATISTICS_BESIDE_A_SIBLING, variables=dict(clientId=self.CLIENT_CODE))
        payload = response.json()
        assert payload.get("errors"), payload
        # The defect: `required=True` made the statistics field non-null, so its error propagated
        # to the nearest nullable parent -- `data` -- and took every sibling with it.
        assert payload["data"] is not None, payload
        assert payload["data"]["giddPublicConflictStatistics"] is None, payload
        assert payload["data"]["giddPublicCountries"] == [{"iso3": "NPL"}], payload


class GiddRestYearArgumentValidationTestCase(HelixAPITestCase):
    """The REST year parameters take the same bound, and keep REST's 400."""

    CLIENT_CODE = "gidd-rest-argument-validation"
    CONFLICTS_URL = "/external-api/gidd/conflicts/"

    def setUp(self):
        super().setUp()
        ClientFactory.create(code=self.CLIENT_CODE, is_active=True)
        external_api_cache.set("client_ids", [self.CLIENT_CODE], None)
        ReleaseMetadata.objects.create(
            release_year=RELEASE_YEAR,
            pre_release_year=RELEASE_YEAR - 1,
            modified_by=self.user,
        )
        status_log = StatusLog.objects.create(triggered_by=self.user, status=StatusLog.Status.SUCCESS)
        # `last_updated` reads `completed_at`, which the model does not set on create.
        StatusLog.objects.filter(pk=status_log.pk).update(
            completed_at=datetime.datetime(2024, 5, 13, tzinfo=datetime.timezone.utc)
        )
        country = CountryFactory.create(iso3="NPL", iso2="NP", idmc_short_name="Nepal")
        GiddDisplacement.objects.create(
            country=country,
            iso3=country.iso3,
            country_name=country.idmc_short_name,
            year=RELEASE_YEAR,
            cause=Crisis.CRISIS_TYPE.CONFLICT,
            new_displacement=500,
            total_displacement=5000,
        )

    def tearDown(self):
        external_api_cache.delete("client_ids")
        super().tearDown()

    def get(self, **params):
        return self.client.get(self.CONFLICTS_URL, {"client_id": self.CLIENT_CODE, **params})

    def test_a_whole_year_is_still_accepted(self):
        response = self.get(start_year=RELEASE_YEAR, end_year=RELEASE_YEAR)
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["count"], 1)

    def test_a_fractional_year_is_rejected(self):
        response = self.get(end_year="2023.5")
        self.assertEqual(response.status_code, 400, response.content)

    def test_a_negative_year_is_rejected(self):
        response = self.get(start_year="-1")
        self.assertEqual(response.status_code, 400, response.content)

    def test_an_unrecognised_release_environment_is_still_rejected(self):
        # Pins REST's existing status code: the validation added for GraphQL must not turn a 400
        # into a 500.
        response = self.get(release_environment="PRE-RELEASE")
        self.assertEqual(response.status_code, 400, response.content)
