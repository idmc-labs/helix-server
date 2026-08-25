"""The whole ordering allowlist, in one place, pinned against a snapshot.

The sets themselves live on the models (`Model.ORDERING_ALLOWLIST`), which is where the
chokepoints can reach them — see `utils/graphene/ordering.py`. That locality costs the one
property the old central dict had for free: being able to read every permitted sort key at
once and answer "is this token reachable anywhere?". This test buys it back, and machine-checks
it rather than trusting convention.

Widening a set is a real decision. A to-many token needs a denormalisation behind it or the
list fans out (`test_to_many_ordering_fanout.py`); a token on an unauthenticated GIDD list
widens what an anonymous caller can sort by. Both should be reviewed, and neither can now
happen without this snapshot changing.

To add a key: change the model, run the suite, and update EXPECTED below in the same commit.
"""

from unittest import mock

from django.apps import apps
from django.test import SimpleTestCase, TestCase

from apps.contrib.models import Client
from utils.factories import ClientFactory
from utils.graphene.ordering import get_ordering_allowlist
from utils.graphene.pagination import GatedPageGraphqlPagination, nulls_last_order_queryset

# Measured, not guessed: see test_no_list_field_uses_an_unguarded_pagination_class.
# Dropped by one when the gidd Conflict/Disaster models (and their Country reverse-relation list
# fields) were removed.
SEEN_FLOOR = 70
DYNAMIC_FLOOR = 6

EXPECTED = {
    "contact.Communication": [
        "country__idmc_short_name",
        "created_at",
        "date",
        "id",
        "medium",
        "modified_at",
        "subject",
    ],
    "contact.CommunicationMedium": [
        "id",
        "name",
    ],
    "contact.Contact": [
        "countries_of_operation__idmc_short_name",
        "created_at",
        "full_name",
        "id",
        "modified_at",
        "organization__name",
    ],
    "contextualupdate.ContextualUpdate": [
        "article_title",
        "countries__idmc_short_name",
        "created_at",
        "id",
        "modified_at",
        "publish_date",
        "publishers__name",
        "sources__name",
    ],
    "contrib.BulkApiOperation": [
        "action",
        "completed_at",
        "created_at",
        "failure_count",
        "id",
        "started_at",
        "status",
        "success_count",
    ],
    "contrib.Client": [
        "acronym",
        "code",
        "contact_email",
        "contact_name",
        "contact_website",
        "created_at",
        "created_by",
        "created_by__full_name",
        "description",
        "id",
        "is_active",
        "last_modified_by",
        "last_modified_by__full_name",
        "modified_at",
        "name",
        "opted_out_of_emails",
        "other_notes",
        "share_source",
        "type",
    ],
    "contrib.ClientTrackInfo": [
        "api_name",
        "api_type",
        "client__code",
        "client__name",
        "id",
        "requests_per_day",
        "tracked_date",
    ],
    "contrib.ExcelDownload": [
        "completed_at",
        "created_at",
        "download_type",
        "file_size",
        "id",
        "modified_at",
        "started_at",
        "status",
    ],
    "country.ContextualAnalysis": [
        "created_at",
        "id",
        "modified_at",
    ],
    "country.Country": [
        "geographical_group__name",
        "id",
        "idmc_short_name",
        "region__name",
        "total_flow_conflict",
        "total_flow_disaster",
        "total_stock_conflict",
        "total_stock_disaster",
    ],
    "country.CountryRegion": [
        "id",
        "name",
    ],
    "country.GeographicalGroup": [
        "id",
        "name",
    ],
    "country.HouseholdSize": [
        "country",
        "created_at",
        "id",
        "modified_at",
        "reference_date",
        "size",
        "year",
    ],
    "country.MonitoringSubRegion": [
        "id",
        "name",
    ],
    "country.Summary": [
        "created_at",
        "id",
        "modified_at",
    ],
    "crisis.Crisis": [
        "countries__idmc_short_name",
        "created_at",
        "created_by__full_name",
        "crisis_type",
        "end_date",
        "event_count",
        "id",
        "modified_at",
        "name",
        "progress",
        "review_approved_count",
        "review_in_progress_count",
        "review_not_started_count",
        "review_re_request_count",
        "start_date",
        "total_count",
        "total_flow_nd_figures",
        "total_stock_idp_figures",
    ],
    "entry.DisaggregatedAge": [
        "age_from",
        "age_to",
        "id",
        "sex",
        "value",
    ],
    "entry.Entry": [
        "article_title",
        "created_at",
        "created_by__full_name",
        "id",
        "modified_at",
        "publish_date",
        "publishers__name",
    ],
    "entry.Figure": [
        "category",
        "country__idmc_short_name",
        "created_at",
        "created_by__full_name",
        "entry__article_title",
        "event__crisis__name",
        "event__name",
        "figure_cause",
        "flow_end_date",
        "flow_start_date",
        "geolocations",
        "id",
        "modified_at",
        "role",
        "sources_reliability",
        "stock_date",
        "stock_reporting_date",
        "term",
        "total_figures",
    ],
    "entry.FigureLocation": [
        "city",
        "country",
        "country_code",
        "display_name",
        "id",
        "identifier",
        "name",
        "state",
    ],
    "entry.FigureTag": [
        "created_at",
        "created_by__full_name",
        "id",
        "modified_at",
        "name",
    ],
    "event.Actor": [
        "country__idmc_short_name",
        "created_at",
        "id",
        "modified_at",
        "name",
        "torg",
    ],
    "event.ContextOfViolence": [
        "created_at",
        "created_by__full_name",
        "id",
        "modified_at",
        "name",
    ],
    "event.DisasterCategory": [
        "id",
        "name",
    ],
    "event.DisasterSubCategory": [
        "id",
        "name",
    ],
    "event.DisasterSubType": [
        "id",
        "name",
    ],
    "event.DisasterType": [
        "id",
        "name",
    ],
    "event.Event": [
        "countries__idmc_short_name",
        "created_at",
        "created_by__full_name",
        "crisis__name",
        "end_date",
        "entry_count",
        "event_type",
        "id",
        "modified_at",
        "name",
        "progress",
        "review_approved_count",
        "review_in_progress_count",
        "review_not_started_count",
        "review_re_request_count",
        "start_date",
        "total_count",
        "total_flow_nd_figures",
        "total_stock_idp_figures",
    ],
    "event.OsvSubType": [
        "id",
        "name",
    ],
    "event.OtherSubType": [
        "created_at",
        "id",
        "modified_at",
        "name",
    ],
    "event.Violence": [
        "id",
        "name",
    ],
    "event.ViolenceSubType": [
        "id",
        "name",
    ],
    "extraction.ExtractionQuery": [
        "created_at",
        "id",
        "modified_at",
    ],
    "gidd.GiddDisplacement": [
        "cause",
        "country_name",
        "hazard_category_name",
        "hazard_sub_category_name",
        "hazard_sub_type_name",
        "hazard_type_name",
        "id",
        "iso3",
        "new_displacement",
        "new_displacement_rounded",
        "total_displacement",
        "total_displacement_rounded",
        "violence_name",
        "violence_sub_type_name",
        "year",
    ],
    "gidd.GiddEventDisplacement": [
        "cause",
        "country_name",
        "end_date",
        "end_date_accuracy",
        "event_codes_type",
        "event_name",
        "hazard_category_name",
        "hazard_sub_category_name",
        "hazard_sub_type_name",
        "hazard_type_name",
        "id",
        "iso3",
        "new_displacement",
        "new_displacement_rounded",
        "start_date",
        "start_date_accuracy",
        "total_displacement",
        "total_displacement_rounded",
        "violence_name",
        "violence_sub_type_name",
        "year",
    ],
    "gidd.PublicFigureAnalysis": [
        "description",
        "figure_category",
        "figure_cause",
        "figures",
        "figures_rounded",
        "id",
        "iso3",
        "year",
    ],
    "gidd.StatusLog": [
        "completed_at",
        "id",
        "status",
        "triggered_at",
        "triggered_by",
    ],
    "hulk.HulkBulkImport": [
        "completed_at",
        "created_at",
        "id",
        "name",
        "started_at",
        "status",
    ],
    "notification.Notification": [
        "created_at",
        "id",
    ],
    "organization.Organization": [
        "category",
        "countries__idmc_short_name",
        "created_at",
        "id",
        "modified_at",
        "name",
        "organization_kind__name",
        "short_name",
    ],
    "organization.OrganizationKind": [
        "created_at",
        "id",
        "modified_at",
        "name",
        "reliability",
    ],
    "parking_lot.ParkedItem": [
        "assigned_to__full_name",
        "comments",
        "created_at",
        "created_by__full_name",
        "id",
        "modified_at",
        "status",
        "title",
        "url",
    ],
    "report.Report": [
        "created_at",
        "created_by__full_name",
        "filter_figure_end_before",
        "filter_figure_start_after",
        "id",
        "modified_at",
        "name",
    ],
    "report.ReportApproval": [
        "created_at",
        "id",
        "is_approved",
        "modified_at",
    ],
    "report.ReportComment": [
        "created_at",
        "id",
        "modified_at",
    ],
    "report.ReportGeneration": [
        "created_at",
        "id",
        "modified_at",
    ],
    "review.UnifiedReviewComment": [
        "created_at",
        "id",
        "modified_at",
    ],
    "users.Portfolio": [
        "id",
        "role",
    ],
    "users.User": [
        "date_joined",
        "full_name",
        "id",
        "is_active",
        "is_admin",
        "is_directors_office",
        "is_reporting_team",
    ],
}


def build_registry():
    """Every model that declares a bound, as `{label: sorted(keys)}`."""
    registry = {}
    for model in apps.get_models():
        allowed = get_ordering_allowlist(model)
        if allowed is not None:
            registry[model._meta.label] = sorted(allowed)
    return registry


class TestOrderingAllowlistRegistry(SimpleTestCase):
    def test_registry_matches_the_snapshot(self):
        self.assertEqual(build_registry(), {label: sorted(keys) for label, keys in EXPECTED.items()})

    def test_no_allowlist_is_inherited(self):
        """A model must declare its own bound or have none.

        The registry walk below only re-implements `vars()`, so it would pass even if
        `get_ordering_allowlist` switched to `getattr` -- and no model in the project currently
        has a bounded ancestor, so there is nothing for it to catch. Build the inheritance case
        explicitly and put the real accessor under it.
        """

        class BoundedBase:
            ORDERING_ALLOWLIST = frozenset({"created_at"})

        class Child(BoundedBase):
            pass

        self.assertEqual(get_ordering_allowlist(BoundedBase), frozenset({"created_at"}))
        self.assertIsNone(
            get_ordering_allowlist(Child),
            "a base's bound must not leak to its children -- an abstract model would bound every model built on it",
        )

        for model in apps.get_models():
            for base in model.__mro__[1:]:
                if "ORDERING_ALLOWLIST" in vars(base) and "ORDERING_ALLOWLIST" not in vars(model):
                    self.fail(f"{model._meta.label} would inherit ORDERING_ALLOWLIST from {base.__name__}")

    def test_an_empty_set_is_a_bound_not_an_omission(self):
        """An empty frozenset must read as "nothing is sortable", not as "no bound declared".

        No model ships an empty set today, so this is set up rather than sampled: the property
        belongs to `_ordering_token_allowed`, which tests `allowed is not None` instead of
        truthiness. A truthiness check would silently downgrade a fully closed model to the
        resolvability fallback, which accepts any real column.
        """
        self.assertIsNotNone(get_ordering_allowlist(Client))
        with mock.patch.object(Client, "ORDERING_ALLOWLIST", frozenset()):
            self.assertEqual(get_ordering_allowlist(Client), frozenset())
            # `name` is a real, ordinarily-allowed column, so only the bound can refuse it.
            with self.assertRaisesMessage(ValueError, "Invalid ordering field: name"):
                nulls_last_order_queryset(Client.objects.all(), "ordering", ordering="name")


class TestEveryPaginatedListIsGated(SimpleTestCase):
    """Every paginated list must reach `order_by()` through a chokepoint.

    The bound is only worth what enforces it. `graphene_django_extras`'
    `graphene_django_extras`' `PageGraphqlPagination.paginate_queryset` calls `qs.order_by(order)`
    raw, so a list wired to it skips the allowlist and hands the caller Django's FieldError with
    every column name in it, while its declared `ORDERING_ALLOWLIST` looks enforced. This walks
    the schema rather than trusting the wiring.
    """

    def test_no_list_field_uses_an_unguarded_pagination_class(self):
        import importlib
        import pkgutil

        import graphene
        from graphene.types.objecttype import ObjectType

        import apps as project_apps
        import helix.schema  # noqa: F401  build the whole type graph before counting
        from utils.graphene.fields import DjangoFilterPaginateListField, DjangoPaginatedListObjectField
        from utils.graphene.pagination import (
            GatedPageGraphqlPagination,
            OrderingOnlyArgumentPagination,
            PageGraphqlPaginationWithoutCount,
        )

        guarded = (PageGraphqlPaginationWithoutCount, OrderingOnlyArgumentPagination, GatedPageGraphqlPagination)

        def subclasses(cls):
            for sub in cls.__subclasses__():
                yield sub
                yield from subclasses(sub)

        # Types carry list fields, and each app's `Query` is a plain class, not an ObjectType.
        holders = set(subclasses(ObjectType))
        for module in pkgutil.iter_modules(project_apps.__path__):
            try:
                schema = importlib.import_module(f"apps.{module.name}.schema")
            except ModuleNotFoundError:
                continue
            holders |= {getattr(schema, name) for name in ("Query", "Mutation") if hasattr(schema, name)}

        # A `graphene.Dynamic` wraps its field in a lambda, so the isinstance check has to look
        # through it -- six list fields (country.crises/events/entries/figures,
        # contextualUpdate.sources/publishers) are declared that way.
        def unwrap(field):
            if isinstance(field, graphene.Dynamic):
                return field.get_type()
            return field

        seen, dynamic_seen, unguarded, unbounded = 0, 0, [], []
        for holder in holders:
            for attr, declared in vars(holder).items():
                field = unwrap(declared)
                if not isinstance(field, (DjangoPaginatedListObjectField, DjangoFilterPaginateListField)):
                    continue
                seen += 1
                if isinstance(declared, graphene.Dynamic):
                    dynamic_seen += 1
                where = f"{holder.__module__}.{holder.__name__}.{attr}"
                if not isinstance(getattr(field, "pagination", None), guarded):
                    unguarded.append(where)
                model = getattr(getattr(field.type, "_meta", None), "model", None)
                if model is not None and vars(model).get("ORDERING_ALLOWLIST") is None:
                    unbounded.append(f"{where} -> {model._meta.label}")
        # Floors, so a walk that silently sees less than the schema holds cannot pass. The Dynamic
        # count is separate because `unwrap` is the only reason those fields are visible at all:
        # without it they vanish from the walk while the total stays above any loose floor.
        self.assertGreaterEqual(seen, SEEN_FLOOR, f"the walk saw only {seen} list fields")
        self.assertGreaterEqual(dynamic_seen, DYNAMIC_FLOOR, f"the unwrap found only {dynamic_seen}")
        self.assertEqual(sorted(unguarded), [], "these lists bypass every ordering chokepoint")
        # The bound is mandatory, not opt-in: a model with no ORDERING_ALLOWLIST is bounded only
        # by resolvability, which accepts to-many paths (the parent fans out, so rows repeat
        # inside a page) and relation hops onto columns the target model's own set excludes.
        self.assertEqual(sorted(unbounded), [], "these list-backing models declare no allowlist")


class TestGatedPaginationCompletesTheSortKey(TestCase):
    """`GatedPageGraphqlPagination` must page on a total sort key, like every other list.

    The lists on this class are the only ones that both slice and reach the library's
    `paginate_queryset`, and that method orders on the raw token. A tied sort key then pages in
    plan-dependent order, so a row can arrive on two pages while another is never returned. The
    ordering therefore goes through `nulls_last_order_queryset`; the library keeps the page
    arithmetic, which these tests pin as well so restoring one does not silently cost the other.
    """

    def setUp(self):
        self.pagination = GatedPageGraphqlPagination(page_size_query_param="pageSize")
        # `is_active` is the tie generator: 12 rows over two distinct values.
        self.clients = [
            ClientFactory.create(name=f"client-{i:02d}", code=f"code-{i:02d}", is_active=i % 2 == 0) for i in range(12)
        ]

    def order_by_sql(self, **kwargs):
        qs = self.pagination.paginate_queryset(Client.objects.all(), pageSize=10, **kwargs)
        return str(qs.query).split("ORDER BY")[-1]

    def test_a_requested_sort_key_gets_the_pk_tiebreaker(self):
        # The tiebreaker follows the lead key's direction, so a tie group reads the same way
        # round as the sort the caller asked for.
        ascending = self.order_by_sql(ordering="is_active")
        self.assertIn('"contrib_client"."id" ASC', ascending, f"no pk tiebreaker in: {ascending}")
        descending = self.order_by_sql(ordering="-is_active")
        self.assertIn('"contrib_client"."id" DESC', descending, f"no pk tiebreaker in: {descending}")

    def test_a_requested_sort_key_gets_nulls_last(self):
        self.assertIn("NULLS LAST", self.order_by_sql(ordering="-other_notes"))

    def test_an_unordered_list_still_pages_deterministically(self):
        self.assertIn('"contrib_client"."id" ASC', self.order_by_sql())

    def test_a_tied_sort_key_pages_without_repeats_or_gaps(self):
        seen = []
        for page in (1, 2, 3):
            seen += [
                obj.pk
                for obj in self.pagination.paginate_queryset(
                    Client.objects.all(), page=page, pageSize=4, ordering="is_active"
                )
            ]
        self.assertEqual(len(seen), len(set(seen)), "a row came back on more than one page")
        self.assertEqual(set(seen), {c.pk for c in self.clients}, "paging skipped a row")

    def test_a_disallowed_token_is_still_refused(self):
        # A real Client column that the allowlist omits, so only the allowlist arm can refuse it
        # -- an unresolvable token would be refused by the fallback whatever the allowlist says.
        with self.assertRaises(ValueError) as cm:
            self.order_by_sql(ordering="use_cases")
        self.assertEqual(str(cm.exception), "Invalid ordering field: use_cases")

    def test_the_library_page_arithmetic_survives(self):
        # A negative page is a full page counted back from the end, not the remainder.
        newest_first = [c.pk for c in reversed(self.clients)]
        last_page = self.pagination.paginate_queryset(Client.objects.all(), page=-1, pageSize=5, ordering="-id")
        self.assertEqual([obj.pk for obj in last_page], newest_first[-5:], "a negative page must count from the end")

        clamped = self.pagination.paginate_queryset(Client.objects.all(), page=1, pageSize=10_000)
        self.assertEqual(clamped.query.high_mark, self.pagination.max_page_size, "an oversize pageSize must clamp")

        self.assertEqual(
            list(self.pagination.paginate_queryset(Client.objects.all(), page=1, pageSize=0)),
            [],
            "pageSize 0 must yield no rows",
        )
        with self.assertRaises(Exception):
            self.pagination.paginate_queryset(Client.objects.all(), page=0, pageSize=5)
