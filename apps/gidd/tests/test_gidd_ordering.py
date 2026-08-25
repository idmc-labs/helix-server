"""`?ordering=` on the public GIDD REST lists, and the tiebreaker that makes it total.

`GiddOrderingFilter` (apps/gidd/views.py) completes a caller's sort key with the primary key,
the same rule `nulls_last_order_queryset` applies to the GraphQL lists -- the Client side of it
is pinned in `apps/contrib/tests/test_ordering_allowlist_registry.py`. These endpoints page by
OFFSET, so a sort key with ties has no stable page boundary: the database is free to return a
tie group in a different order per request, which lets a row arrive on two pages while another
is never returned at all.

The direction of the tiebreak follows the LEADING key, so a tie group reads the same way round
as the sort that was asked for.
"""

from rest_framework.exceptions import ValidationError
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

from apps.gidd.models import Conflict, GiddDisplacement, GiddEventDisplacement, ReleaseMetadata
from apps.gidd.views import ConflictViewSet, DisasterViewSet
from apps.crisis.models import Crisis
from helix.caches import external_api_cache
from utils.factories import ClientFactory, CountryFactory
from utils.tests import HelixAPITestCase

CONFLICTS_URL = "/external-api/gidd/conflicts/"

# `ReleaseMetadataFilter` caps every list at the configured release year, so fixture rows dated
# past it are dropped and the tests would run against an empty queryset.
RELEASE_YEAR = 2024
DATA_YEARS = (RELEASE_YEAR - 5, RELEASE_YEAR - 4)

PK_SQL = f'"{Conflict._meta.db_table}"."{Conflict._meta.pk.column}"'
YEAR_SQL = f'"{Conflict._meta.db_table}"."year"'
ISO3_SQL = f'"{Conflict._meta.db_table}"."iso3"'

ROW_COUNT = 12
PAGE_SIZE = 4


class GiddConflictListMixin:
    """What a GIDD list request needs before it can return a row.

    The endpoints are unauthenticated, but `track_gidd` refuses a client id that is absent from
    the redis registry or backed by an inactive row, and the list filterset raises when no
    `ReleaseMetadata` exists. Follows `apps/gidd/tests/test_rest_api.py`.
    """

    CLIENT_CODE = "gidd-ordering-client"

    def setUp(self):
        super().setUp()
        ClientFactory.create(code=self.CLIENT_CODE, is_active=True)
        external_api_cache.set("client_ids", [self.CLIENT_CODE], None)
        ReleaseMetadata.objects.create(
            release_year=RELEASE_YEAR,
            pre_release_year=RELEASE_YEAR - 1,
            modified_by=self.user,
        )
        self.country = CountryFactory.create(iso3="AFG", iso2="AF", idmc_short_name="Afghanistan")

    def tearDown(self):
        external_api_cache.delete("client_ids")
        super().tearDown()

    def create_conflict(self, year, new_displacement):
        # `iso3` and `country_name` are denormalised onto the row, so they are set from the
        # country rather than left to diverge from it.
        return Conflict.objects.create(
            country=self.country,
            iso3=self.country.iso3,
            country_name=self.country.idmc_short_name,
            year=year,
            new_displacement=new_displacement,
        )


class TestGiddOrderingIsTotal(GiddConflictListMixin, HelixAPITestCase):
    """The compiled ORDER BY, driven through the view's real backend chain."""

    def setUp(self):
        super().setUp()
        self.factory = APIRequestFactory()
        # Rows, so the ORDER BY under test belongs to a queryset that actually returns
        # something: a chain that had filtered everything away would compile the same SQL.
        for index, year in enumerate(DATA_YEARS):
            self.create_conflict(year, index)

    def order_by_sql(self, ordering):
        request = self.factory.get(CONFLICTS_URL, {"client_id": self.CLIENT_CODE, "ordering": ordering})
        view = ConflictViewSet()
        view.action = "list"
        view.args, view.kwargs = (), {}
        view.request = Request(request)
        # `get_queryset()` is bypassed on purpose: it tracks the client id as a side effect, and
        # the ordering backend only ever sees the queryset handed to `filter_queryset`.
        queryset = view.filter_queryset(Conflict.objects.all())
        assert queryset.count() == len(DATA_YEARS), f"the filter chain returned {queryset.count()} rows"
        return str(queryset.query).split("ORDER BY")[-1].strip()

    def test_an_ascending_sort_key_gets_an_ascending_pk_tiebreak(self):
        order_by = self.order_by_sql("year")
        assert order_by.startswith(f"{YEAR_SQL} ASC"), order_by
        assert order_by.endswith(f"{PK_SQL} ASC"), f"no trailing pk tiebreaker in: {order_by}"

    def test_a_descending_sort_key_gets_a_descending_pk_tiebreak(self):
        order_by = self.order_by_sql("-year")
        assert order_by.startswith(f"{YEAR_SQL} DESC"), order_by
        assert order_by.endswith(f"{PK_SQL} DESC"), f"no descending pk tiebreaker in: {order_by}"

    def test_the_leading_key_decides_the_tiebreak_direction(self):
        # `iso3` leads and `-year` follows: the tiebreak reads off the lead key, so a trailing
        # descending key must not flip it.
        order_by = self.order_by_sql("iso3,-year")
        assert order_by.startswith(f"{ISO3_SQL} ASC"), order_by
        assert f"{YEAR_SQL} DESC" in order_by, order_by
        assert order_by.endswith(f"{PK_SQL} ASC"), f"the trailing key decided the tiebreak: {order_by}"


class TestGiddOrderingPagesTiesStably(GiddConflictListMixin, HelixAPITestCase):
    """The property the tiebreaker exists for, which no single page can show."""

    def setUp(self):
        super().setUp()
        # `new_displacement` identifies the row: the conflict serializer exposes no `id`, and
        # `year` is the tie generator, so it is the only per-row value a page can be read by.
        self.markers = list(range(1, ROW_COUNT + 1))
        for marker in self.markers:
            self.create_conflict(DATA_YEARS[marker % len(DATA_YEARS)], marker)

    def page(self, offset):
        response = self.client.get(
            CONFLICTS_URL,
            {"client_id": self.CLIENT_CODE, "ordering": "year", "limit": PAGE_SIZE, "offset": offset},
        )
        assert response.status_code == 200, response.content
        return response.json()

    def test_a_tied_sort_key_pages_without_repeats_or_gaps(self):
        seen, years = [], []
        for offset in range(0, ROW_COUNT, PAGE_SIZE):
            payload = self.page(offset)
            assert payload["count"] == ROW_COUNT, f"the list held {payload['count']} rows, not {ROW_COUNT}"
            results = payload["results"]
            assert len(results) == PAGE_SIZE, f"offset {offset} returned {len(results)} rows"
            seen += [row["new_displacement"] for row in results]
            years += [row["year"] for row in results]

        assert len(seen) == len(set(seen)), f"a row came back on more than one page: {seen}"
        assert set(seen) == set(self.markers), f"paging skipped a row: {sorted(set(self.markers) - set(seen))}"
        assert years == sorted(years), f"the requested sort did not hold across pages: {years}"


class GiddComputedFieldOrderingTest(GiddConflictListMixin, HelixAPITestCase):
    """Sort keys whose serializer field is computed rather than stored.

    `*_rounded` and `event_codes` are `SerializerMethodField`s, so DRF reports `source == "*"` and
    the filter cannot derive an ORM path; an unresolved term is refused with a 400.
    `ORDERING_SOURCES` names the column a term is computed from, for the rounded figures only:
    rounding is monotonic, so the raw column gives the same order. `event_codes` carries no
    mapping, so sorting by it is refused.
    """

    def setUp(self):
        super().setUp()
        self.factory = APIRequestFactory()
        country = self.create_country("AFG", "Afghanistan")
        for index, year in enumerate(DATA_YEARS):
            self.create_displacement(country, year, index)

    def order_by_sql(self, view_class, queryset, ordering):
        request = self.factory.get("/", {"client_id": self.CLIENT_CODE, "ordering": ordering})
        view = view_class()
        view.action = "list"
        view.args, view.kwargs = (), {}
        view.request = Request(request)
        return str(view.filter_queryset(queryset).query).split("ORDER BY")[-1].strip()

    def test_a_rounded_term_sorts_on_the_column_it_is_computed_from(self):
        for term, column in (
            ("new_displacement_rounded", "new_displacement"),
            ("total_displacement_rounded", "total_displacement"),
        ):
            with self.subTest(term=term):
                sql = self.order_by_sql(ConflictViewSet, GiddDisplacement.objects.all(), term)
                self.assertIn(column, sql)

    def test_an_event_codes_term_is_refused(self):
        for term in ("event_codes", "event_codes_type"):
            with self.subTest(term=term):
                with self.assertRaises(ValidationError):
                    self.order_by_sql(DisasterViewSet, GiddEventDisplacement.objects.all(), term)

    def test_an_unknown_term_is_still_refused(self):
        with self.assertRaises(ValidationError):
            self.order_by_sql(ConflictViewSet, GiddDisplacement.objects.all(), "not_a_column")
