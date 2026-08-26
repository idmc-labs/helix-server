"""`?ordering=` on the public GIDD REST lists, and the tiebreaker that makes it total.

`GiddOrderingFilter` (apps/gidd/views.py) completes a caller's sort key so that no two result
rows compare equal. Which columns do that depends on the queryset: a row-level queryset is made
total by its primary key, an aggregate by its GROUP BY keys -- an aggregate has no pk of its own,
and ordering one by `id` folds `id` into the group, so the page carries one row per underlying
row while `count()`, which clears ordering, keeps reporting the grouped total.

These endpoints page by OFFSET, so a sort key with ties has no stable page boundary: the database
is free to return a tie group in a different order per request, which lets a row arrive on two
pages while another is never returned at all.

The direction of the tiebreak follows the LEADING key, so a tie group reads the same way round
as the sort that was asked for. The Client side of the same rule is pinned in
`apps/contrib/tests/test_ordering_allowlist_registry.py`.
"""

from django.db.models import F, Q, Sum
from django.test import TestCase
from rest_framework.exceptions import ValidationError
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

from apps.crisis.models import Crisis
from apps.gidd.models import GiddDisplacement, GiddEventDisplacement, ReleaseMetadata
from apps.gidd.schema import cause_typology_filters
from apps.gidd.views import ConflictViewSet, DisasterViewSet
from helix.caches import external_api_cache
from utils.db import tiebreak_fields
from utils.factories import ClientFactory, CountryFactory
from utils.tests import HelixAPITestCase

CONFLICTS_URL = "/external-api/gidd/conflicts/"

# `ReleaseMetadataFilter` caps every list at the configured release year, so fixture rows dated
# past it are dropped and the tests would run against an empty queryset.
RELEASE_YEAR = 2024
DATA_YEARS = (RELEASE_YEAR - 5, RELEASE_YEAR - 4)

PK_SQL = f'"{GiddDisplacement._meta.db_table}"."{GiddDisplacement._meta.pk.column}"'
YEAR_SQL = f'"{GiddDisplacement._meta.db_table}"."year"'
ISO3_SQL = f'"{GiddDisplacement._meta.db_table}"."iso3"'

# `/gidd/conflicts/` aggregates `GiddDisplacement` to one row per country x year, so a tie group
# has to be built out of distinct countries sharing a year.
COUNTRY_COUNT = 12
PAGE_SIZE = 4
ROWS_PER_COUNTRY = 2
FIRST_ROW_FIGURE = 1
SECOND_ROW_FIGURE = 2


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

    def tearDown(self):
        external_api_cache.delete("client_ids")
        super().tearDown()

    def create_country(self, iso3, name):
        # `iso2` is left unset: nothing on these lists reads it.
        return CountryFactory.create(iso3=iso3, idmc_short_name=name)

    def create_displacement(self, country, year, new_displacement, violence_sub_type_name=None):
        # `iso3` and `country_name` are denormalised onto the row -- the endpoint groups on the
        # denormalised columns, not on the FK -- so they are set from the country rather than
        # left to diverge from it. `cause` is what the conflict list filters on.
        return GiddDisplacement.objects.create(
            country=country,
            iso3=country.iso3,
            country_name=country.idmc_short_name,
            year=year,
            cause=Crisis.CRISIS_TYPE.CONFLICT,
            violence_sub_type_name=violence_sub_type_name,
            new_displacement=new_displacement,
            total_displacement=new_displacement,
        )


class TestGiddOrderingIsTotal(GiddConflictListMixin, HelixAPITestCase):
    """The compiled ORDER BY, driven through the view's real backend chain.

    A PLAIN queryset on purpose: it is the branch of `tiebreak_fields` that resolves to the
    primary key, and the pk is a single column whose position in the compiled ORDER BY can be
    asserted exactly. The aggregate branch is covered by `TestGiddOrderingPagesTiesStably`.
    """

    def setUp(self):
        super().setUp()
        self.factory = APIRequestFactory()
        self.country = self.create_country("AFG", "Afghanistan")
        # Rows, so the ORDER BY under test belongs to a queryset that actually returns
        # something: a chain that had filtered everything away would compile the same SQL.
        for index, year in enumerate(DATA_YEARS):
            self.create_displacement(self.country, year, index)

    def order_by_sql(self, ordering):
        request = self.factory.get(CONFLICTS_URL, {"client_id": self.CLIENT_CODE, "ordering": ordering})
        view = ConflictViewSet()
        view.action = "list"
        view.args, view.kwargs = (), {}
        view.request = Request(request)
        # `get_queryset()` is bypassed on purpose: it tracks the client id as a side effect, it
        # returns the aggregate rather than a row-level queryset, and the ordering backend only
        # ever sees the queryset handed to `filter_queryset`.
        queryset = view.filter_queryset(GiddDisplacement.objects.all())
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
    """The property the tiebreaker exists for, which no single page can show.

    This is also the ONLY direct coverage of the GROUP-BY-key tiebreak: `/gidd/conflicts/` is a
    `.values().annotate()` aggregate, so `tiebreak_fields` returns `iso3`, `country_name` and
    `year` here rather than the pk. Ordering this queryset by pk instead would fold `id` into the
    GROUP BY and hand back one row per stored row, while `count()` -- which clears ordering --
    would keep reporting the grouped total: page and count would disagree, and the assertions
    below would fail on both.

    The tie group is built at the aggregate's grain: several COUNTRIES share a `year`, so they
    tie on the requested sort key and are separated only by `iso3`. Six countries per year
    against a four-row page means a tie group straddles two page boundaries.
    """

    def setUp(self):
        super().setUp()
        # The conflict serializer exposes no `id`, and `year` is the tie generator, so `iso3` is
        # what a page is read by.
        self.year_by_iso3 = {}
        for index in range(COUNTRY_COUNT):
            iso3 = f"T{index:02d}"
            # `year` alternates while `iso3` ascends, so the expected sequence is NOT sorted
            # `iso3`: a page must respect the requested key AND the tiebreak, not either alone.
            year = DATA_YEARS[index % len(DATA_YEARS)]
            country = self.create_country(iso3, f"Country {index:02d}")
            self.create_displacement(country, year, FIRST_ROW_FIGURE, "International armed conflict")
            self.create_displacement(country, year, SECOND_ROW_FIGURE, "Civil unrest")
            self.year_by_iso3[iso3] = year

        # Non-vacuity guard: the stored grain must differ from the published one, or an
        # aggregate that leaked its underlying rows would page identically.
        assert GiddDisplacement.objects.count() == COUNTRY_COUNT * ROWS_PER_COUNTRY

    @property
    def expected_order(self):
        return [iso3 for _, iso3 in sorted((year, iso3) for iso3, year in self.year_by_iso3.items())]

    def page(self, offset):
        response = self.client.get(
            CONFLICTS_URL,
            {"client_id": self.CLIENT_CODE, "ordering": "year", "limit": PAGE_SIZE, "offset": offset},
        )
        assert response.status_code == 200, response.content
        return response.json()

    def test_a_tied_sort_key_pages_without_repeats_or_gaps(self):
        seen, years = [], []
        for offset in range(0, COUNTRY_COUNT, PAGE_SIZE):
            payload = self.page(offset)
            assert payload["count"] == COUNTRY_COUNT, f"the list held {payload['count']} rows, not {COUNTRY_COUNT}"
            results = payload["results"]
            assert len(results) == PAGE_SIZE, f"offset {offset} returned {len(results)} rows"
            # The page carries the aggregate, not the rows it was summed from.
            for row in results:
                assert row["new_displacement"] == FIRST_ROW_FIGURE + SECOND_ROW_FIGURE, row
            seen += [row["iso3"] for row in results]
            years += [row["year"] for row in results]

        assert len(seen) == len(set(seen)), f"a row came back on more than one page: {seen}"
        assert set(seen) == set(self.year_by_iso3), f"paging skipped a row: {sorted(set(self.year_by_iso3) - set(seen))}"
        assert years == sorted(years), f"the requested sort did not hold across pages: {years}"
        assert seen == self.expected_order, f"the tie group was not ordered by the group keys: {seen}"


class GiddComputedFieldOrderingTest(GiddConflictListMixin, HelixAPITestCase):
    """Sort keys whose serializer field is computed rather than stored.

    `*_rounded` and `event_codes` are `SerializerMethodField`s, so DRF reports `source == "*"` and
    the filter cannot derive an ORM path; an unresolved term is refused with a 400. These sorts
    were accepted before the endpoints moved onto the new tables, so `ORDERING_SOURCES` names the
    column each one is computed from. Rounding is monotonic, so the raw column gives the same
    order.
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

    def test_an_event_codes_term_sorts_on_the_stored_all_country_column(self):
        for term, column in (
            ("event_codes", "all_country_event_codes"),
            ("event_codes_type", "all_country_event_codes_type"),
        ):
            with self.subTest(term=term):
                sql = self.order_by_sql(DisasterViewSet, GiddEventDisplacement.objects.all(), term)
                self.assertIn(column, sql)

    def test_an_unknown_term_is_still_refused(self):
        with self.assertRaises(ValidationError):
            self.order_by_sql(ConflictViewSet, GiddDisplacement.objects.all(), "not_a_column")


class TestTiebreakFollowsTheSort(TestCase):
    """What `tiebreak_fields` appends to an ordering the caller already has.

    Both call sites append a tiebreak, and only the REST one used to read the sort's direction: the
    country-year resolver appended a fixed `.asc()`, so a tie group read backwards under a
    descending sort. The direction and the de-duplication live in the helper now, so a caller cannot
    get one right and the other wrong.
    """

    def plain(self):
        return GiddDisplacement.objects.all()

    def grouped(self):
        return GiddDisplacement.objects.values("iso3", "year").annotate(total=Sum("new_displacement"))

    def test_without_an_ordering_the_bare_columns_come_back(self):
        assert tiebreak_fields(self.plain()) == ["id"]
        assert tiebreak_fields(self.grouped()) == ["iso3", "year"]

    def test_an_ascending_sort_takes_an_ascending_tiebreak(self):
        assert tiebreak_fields(self.plain(), ["country_name"]) == ["id"]

    def test_a_descending_sort_takes_a_descending_tiebreak(self):
        assert tiebreak_fields(self.plain(), ["-country_name"]) == ["-id"]
        assert tiebreak_fields(self.grouped(), ["-total"]) == ["-iso3", "-year"]

    def test_a_column_already_sorted_on_is_not_repeated(self):
        assert tiebreak_fields(self.grouped(), ["iso3"]) == ["year"]
        assert tiebreak_fields(self.grouped(), ["-iso3", "year"]) == []

    def test_an_order_by_expression_counts_as_already_sorted(self):
        # The GraphQL resolver builds `F(...).desc(nulls_last=True)`, not strings, so a helper that
        # only understood strings would append a duplicate key it could not see.
        ordering = [F("iso3").desc(nulls_last=True)]
        assert tiebreak_fields(self.grouped(), ordering) == ["-year"]


class TestCountryQueryTypologyFilters(TestCase):
    """Which typology arguments the country queries accept.

    They took `hazardTypes` only, while the statistics and event queries took all four hazard
    levels, so a caller bounding by category had to enumerate its types. The builder is shared by
    both country resolvers so the pair cannot drift apart again.
    """

    def build(self, **kwargs):
        return cause_typology_filters(kwargs)

    def test_every_hazard_level_narrows_the_disaster_side(self):
        for argument, column in (
            ("hazard_categories", "hazard_category"),
            ("hazard_sub_categories", "hazard_sub_category"),
            ("hazard_types", "hazard_type"),
            ("hazard_sub_types", "hazard_sub_type"),
        ):
            with self.subTest(argument=argument):
                _, disaster = self.build(**{argument: [1]})
                assert f"{column}__in" in str(disaster), f"{argument} did not reach the disaster filter"

    def test_violence_levels_narrow_the_conflict_side(self):
        conflict, _ = self.build(violence_types=[1], violence_sub_types=[2])
        assert "violence__in" in str(conflict)
        assert "violence_sub_type__in" in str(conflict)

    def test_the_arguments_are_consumed_so_the_filterset_never_sees_them(self):
        # `GiddCountryDisplacementFilter` does not declare them; a leftover key would be handed to
        # django-filter, which ignores it, and the caller's narrowing would silently do nothing.
        kwargs = {"hazard_categories": [1], "violence_types": [2], "countries_iso3": ["NPL"]}
        cause_typology_filters(kwargs)
        assert kwargs == {"countries_iso3": ["NPL"]}

    def test_an_absent_argument_leaves_the_cause_filter_alone(self):
        conflict, disaster = self.build()
        assert str(conflict) == str(Q(cause=Crisis.CRISIS_TYPE.CONFLICT))
        assert str(disaster) == str(Q(cause=Crisis.CRISIS_TYPE.DISASTER))
