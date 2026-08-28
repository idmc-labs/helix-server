"""`?limit=` on the paginated GIDD REST lists is bounded by `GIDD_REST_MAX_PAGE_SIZE`.

Without a bound one request could ask for every row in the table. The bound defaults to the
one the GIDD GraphQL fields already enforce, so the same public data pages the same way on
either surface.

DRF clamps silently and still advertises `next`, so the contract is "a page plus a link and
the full count", never an error and never a short page with `next: null`. That last
combination would be silent data loss for a caller that does not follow the link, and it is
what `test_a_clamped_page_advertises_a_next_link` pins.

The tests override the bound rather than seeding rows past it, so they stay meaningful if the
shared value changes.
"""

from django.test import override_settings

from apps.gidd.paginations import GiddLimitOffsetPagination
from apps.gidd.views import (
    ConflictViewSet,
    CountryViewSet,
    DisaggregationViewSet,
    DisasterViewSet,
    DisplacementDataViewSet,
    PublicFigureAnalysisViewSet,
)
from utils.factories import CountryFactory
from utils.tests import HelixAPITestCase

from .test_rest_api import COUNTRIES_URL, GiddRestApiMixin

PAGINATED_VIEWSETS = (
    CountryViewSet,
    ConflictViewSet,
    DisasterViewSet,
    DisplacementDataViewSet,
    PublicFigureAnalysisViewSet,
)

# Export actions must stay uncapped.
EXPORT_ACTIONS = (
    (DisasterViewSet, "export"),
    (DisplacementDataViewSet, "export"),
    (DisaggregationViewSet, "export_disaggregated_geojson"),
    (DisaggregationViewSet, "export_disaggregated"),
)


class TestGiddRestPaginationCap(GiddRestApiMixin, HelixAPITestCase):
    def setUp(self):
        super().setUp()
        # The mixin creates two; a third makes a cap of 2 a partial page.
        self.country_ind = CountryFactory.create(iso3="IND", iso2="IN", idmc_short_name="India")

    def test_every_paginated_list_endpoint_uses_the_capped_paginator(self):
        for viewset in PAGINATED_VIEWSETS:
            with self.subTest(viewset=viewset.__name__):
                self.assertIs(viewset.pagination_class, GiddLimitOffsetPagination)

    @override_settings(GIDD_REST_MAX_PAGE_SIZE=1234)
    def test_the_cap_is_read_from_settings_per_request(self):
        # `LimitOffsetPagination` leaves `max_limit` None, the unbounded case; a cap bound at
        # import time, or one not sourced from settings at all, misses the override.
        self.assertEqual(GiddLimitOffsetPagination().max_limit, 1234)

    @override_settings(GIDD_REST_MAX_PAGE_SIZE=2)
    def test_a_limit_above_the_cap_is_clamped(self):
        payload = self.get_list(COUNTRIES_URL, limit=10_000)
        self.assertEqual(len(payload["results"]), 2)
        # The full row count is still reported, so a caller can tell there is more.
        self.assertEqual(payload["count"], 3)

    @override_settings(GIDD_REST_MAX_PAGE_SIZE=2)
    def test_a_clamped_page_advertises_a_next_link(self):
        payload = self.get_list(COUNTRIES_URL, limit=10_000)
        self.assertIsNotNone(payload["next"], "a clamped page without `next` is silent truncation")

    @override_settings(GIDD_REST_MAX_PAGE_SIZE=2)
    def test_following_the_next_link_yields_the_remaining_rows(self):
        first = self.get_list(COUNTRIES_URL, limit=10_000)
        # Verbatim, with no query of our own: the link has to carry the offset AND the client id,
        # or a caller that follows it gets a 403 rather than the rest of the rows.
        response = self.client.get(first["next"])
        self.assertEqual(response.status_code, 200, response.content)
        rest = response.json()
        seen = [row["iso3"] for row in first["results"]] + [row["iso3"] for row in rest["results"]]
        self.assertCountEqual(seen, ["AFG", "NPL", "IND"])
        self.assertIsNone(rest["next"], "the last page must not advertise another one")

    @override_settings(GIDD_REST_MAX_PAGE_SIZE=1_000)
    def test_a_limit_below_the_cap_is_honoured(self):
        # Two of the three rows, so a paginator that ignored `limit` would return three.
        payload = self.get_list(COUNTRIES_URL, limit=2)
        self.assertEqual(len(payload["results"]), 2)
        self.assertEqual(payload["count"], 3)
        self.assertIsNotNone(payload["next"])

    def test_export_actions_are_not_paginated_and_so_are_not_capped(self):
        for viewset, action_name in EXPORT_ACTIONS:
            with self.subTest(viewset=viewset.__name__, action=action_name):
                action = getattr(viewset, action_name)
                self.assertIn("pagination_class", action.kwargs)
                self.assertIsNone(action.kwargs["pagination_class"])
