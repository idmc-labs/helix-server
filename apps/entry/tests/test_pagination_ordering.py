from django.db.models import Case, F, When
from django.db.models.functions import Lower
from django.test import SimpleTestCase

from apps.entry.models import Figure
from apps.event.models import Violence, ViolenceSubType
from apps.report.models import ReportComment
from utils.factories import CountryFactory, EntryFactory, EventFactory, FigureFactory, ViolenceFactory
from utils.graphene.dataloaders import _ordering_expressions
from utils.graphene.ordering import get_ordering_allowlist, leads_descending, orders_by_pk
from utils.graphene.pagination import OrderingOnlyArgumentPagination, nulls_last_order_queryset
from utils.tests import HelixTestCase


class TestEmptyOrderingFallback(HelixTestCase):
    """Paginating with no requested ordering must not slice plan-dependent physical order.

    `nulls_last_order_queryset` falls back to pk ASC, and an ordering the queryset already
    carries is kept and completed with a pk tiebreaker rather than trusted as it stands: both
    `Meta.ordering` and a filterset's bucket are non-unique, so the rows tying on them would
    otherwise page in plan-dependent order.
    """

    def setUp(self) -> None:
        country = CountryFactory.create()
        event = EventFactory.create()
        entry = EntryFactory.create()
        self.figs = FigureFactory.create_batch(3, entry=entry, event=event, country=country)

    def test_unordered_queryset_falls_back_to_pk_asc(self):
        # ascending pk: deterministic AND preserves the de-facto insertion order
        # unordered lists (e.g. the public GIDD endpoints) have always returned
        qs = nulls_last_order_queryset(Figure.objects.all(), "ordering")
        self.assertTrue(qs.ordered)
        self.assertEqual([f.id for f in qs], sorted(f.id for f in self.figs))

    def test_already_ordered_queryset_is_respected(self):
        qs = nulls_last_order_queryset(Figure.objects.order_by("-id"), "ordering")
        self.assertEqual(
            [f.id for f in qs],
            sorted((f.id for f in self.figs), reverse=True),
        )

    def test_explicit_ordering_still_applies(self):
        qs = nulls_last_order_queryset(Figure.objects.all(), "ordering", ordering="-id")
        self.assertEqual(
            [f.id for f in qs],
            sorted((f.id for f in self.figs), reverse=True),
        )

    def test_a_non_unique_existing_ordering_gains_a_pk_tiebreaker(self):
        qs = nulls_last_order_queryset(Figure.objects.order_by("role"), "ordering")
        self.assertEqual([str(each) for each in qs.query.order_by], ["role", str(F("id").asc())])

    def test_the_tiebreaker_follows_the_existing_leading_key(self):
        qs = nulls_last_order_queryset(Figure.objects.order_by("-role"), "ordering")
        self.assertEqual([str(each) for each in qs.query.order_by], ["-role", str(F("id").desc())])

    def test_meta_ordering_gains_a_pk_tiebreaker(self):
        """`ReportComment.Meta.ordering` is `("-created_at",)`, which is not unique.

        The tiebreaker follows it descending, so a batch created in one transaction still
        reads newest-first inside a tie group.
        """
        qs = nulls_last_order_queryset(ReportComment.objects.all(), "ordering")
        self.assertEqual([str(each) for each in qs.query.order_by], ["-created_at", str(F("id").desc())])

    def test_an_existing_pk_ordering_gets_no_second_tiebreaker(self):
        qs = nulls_last_order_queryset(Figure.objects.order_by("-id"), "ordering")
        self.assertEqual([str(each) for each in qs.query.order_by], ["-id"])


class TestExistingOrderingSurvivesAClientSort(HelixTestCase):
    """A filterset's own `order_by` is prepended, not replaced.

    `OrganizationFilter.filter_order_country_first` buckets the organizations a caller cares
    about to the front by ordering the queryset, and that bucket outranks the sort within it.

    `Meta.ordering` is not prepended: a model default leading every sort would leave the
    client's `ordering` argument with nothing to do.
    """

    def setUp(self) -> None:
        country = CountryFactory.create()
        event = EventFactory.create()
        entry = EntryFactory.create()
        FigureFactory.create_batch(2, entry=entry, event=event, country=country)

    def test_the_querysets_own_ordering_leads(self):
        qs = nulls_last_order_queryset(Figure.objects.order_by("role"), "ordering", ordering="-created_at")
        self.assertEqual(
            [str(each) for each in qs.query.order_by],
            ["role", str(F("created_at").desc(nulls_last=True)), str(F("id").desc())],
        )

    def test_meta_ordering_does_not_lead(self):
        qs = nulls_last_order_queryset(ReportComment.objects.all(), "ordering", ordering="created_at")
        self.assertEqual(
            [str(each) for each in qs.query.order_by],
            [str(F("created_at").asc(nulls_last=True)), str(F("id").asc())],
        )


class TestOrderingHelpers(SimpleTestCase):
    """The expression branches of the ordering helpers.

    `order_by` accepts a bare `F("id")` as well as the `OrderBy` that `F("id").asc()` builds,
    and an expression such as `Case` states no direction at all. Nothing else in the suite
    reaches these branches with anything but a `Case`.
    """

    def test_orders_by_pk_unwraps_expressions(self):
        for key, expected in (
            ("id", True),
            ("-id", True),
            ("pk", True),
            ("name", False),
            (F("id"), True),
            (F("id").asc(), True),
            (F("pk").desc(), True),
            (F("name").asc(), False),
            (Lower("name"), False),
            (Case(When(id__in=[1], then=0), default=1), False),
        ):
            with self.subTest(key=key):
                self.assertEqual(orders_by_pk([key], "id"), expected)

    def test_leads_descending_skips_directionless_keys(self):
        case = Case(When(id__in=[1], then=0), default=1)
        self.assertFalse(leads_descending([]))
        self.assertTrue(leads_descending(["-name"]))
        self.assertFalse(leads_descending(["name"]))
        self.assertTrue(leads_descending([F("name").desc()]))
        # The bucket states no direction, so the tiebreaker follows the first key that does.
        self.assertTrue(leads_descending([case, "-name"]))
        self.assertFalse(leads_descending([case, "name"]))


class TestOrderingAllowlist(HelixTestCase):
    """`ordering` is a free-form client string. For a model with an ORDERING_ALLOWLIST it is bounded
    to the keys the client actually sorts on; every other model keeps the looser
    is-this-resolvable check so an unlisted list degrades rather than breaks."""

    def setUp(self) -> None:
        country = CountryFactory.create()
        event = EventFactory.create()
        entry = EntryFactory.create()
        self.figs = FigureFactory.create_batch(3, entry=entry, event=event, country=country)

    def test_allowlisted_key_is_accepted(self):
        qs = nulls_last_order_queryset(Figure.objects.all(), "ordering", ordering="-created_at")
        self.assertEqual(len(list(qs)), 3)

    def test_resolvable_but_not_allowlisted_key_is_rejected(self):
        # `unit` is a real Figure column and would order fine — no client sorts on it, so a
        # request for it is not something the list is expected to serve.
        with self.assertRaisesMessage(ValueError, "Invalid ordering field: unit"):
            nulls_last_order_queryset(Figure.objects.all(), "ordering", ordering="unit")

    def test_rejection_names_only_the_client_token(self):
        # Leaking the model's field list was what the original check existed to prevent.
        with self.assertRaises(ValueError) as ctx:
            nulls_last_order_queryset(Figure.objects.all(), "ordering", ordering="-zzz__nope")
        self.assertEqual(str(ctx.exception), "Invalid ordering field: zzz__nope")

    def test_a_doubled_direction_prefix_is_rejected(self):
        """`--created_at` must fail the allowlist, not pass it as `created_at`.

        Stripping every leading dash hands the validator an allowlisted key and then builds
        `F("-created_at")`, so the token reaches query compilation and Django's FieldError --
        which enumerates every ORM field -- is what the caller gets back.
        """
        with self.assertRaises(ValueError) as ctx:
            nulls_last_order_queryset(Figure.objects.all(), "ordering", ordering="--created_at")
        self.assertEqual(str(ctx.exception), "Invalid ordering field: -created_at")
        self.assertNotIn("Choices are", str(ctx.exception))

    def test_comma_joined_ordering_is_validated_per_token(self):
        # EntryForm hardcodes this pair, so commas must not be treated as one opaque key.
        qs = nulls_last_order_queryset(Figure.objects.all(), "ordering", ordering="role,created_at")
        self.assertEqual(len(list(qs)), 3)
        with self.assertRaisesMessage(ValueError, "Invalid ordering field: unit"):
            nulls_last_order_queryset(Figure.objects.all(), "ordering", ordering="role,unit")

    def test_unmapped_model_falls_back_to_resolvability(self):
        self.assertIsNone(get_ordering_allowlist(Violence))
        # Not allowlisted anywhere, yet accepted because it resolves...
        nulls_last_order_queryset(Violence.objects.all(), "ordering", ordering="name").exists()
        # ...while junk is still refused by the fallback check.
        with self.assertRaisesMessage(ValueError, "Invalid ordering field: zzz__nope"):
            nulls_last_order_queryset(Violence.objects.all(), "ordering", ordering="zzz__nope")

    def test_junk_after_a_resolvable_hop_is_refused(self):
        """An unresolvable hop refuses the token wherever it sits, not just at the first.

        `violence` resolves and `bogus` does not. Accepting the token because the FIRST hop
        was fine handed it to query compilation, where Django's FieldError enumerates every
        ORM field on the joined model -- the leak the guard exists to prevent, on exactly the
        unbounded lists that have nothing else in front of them.
        """
        self.assertIsNone(get_ordering_allowlist(ViolenceSubType))
        # The first hop really does resolve, so this is not rejected for the trivial reason.
        nulls_last_order_queryset(ViolenceSubType.objects.all(), "ordering", ordering="violence__name").exists()
        with self.assertRaisesMessage(ValueError, "Invalid ordering field: violence__bogus"):
            nulls_last_order_queryset(ViolenceSubType.objects.all(), "ordering", ordering="violence__bogus")


class TestOrderingOnlyArgumentPaginationGuard(HelixTestCase):
    """The SECOND ordering chokepoint.

    `OrderingOnlyArgumentPagination` serves the lists that take no page arguments
    (violenceList, disasterTypeList, contextOfViolenceList, ...) and reaches `order_by()` by
    its own route, never through `nulls_last_order_queryset`. It must apply the same guard,
    or a junk token still returns Django's raw `FieldError` — which enumerates every field on
    the model. The two implementations must not drift, so they are pinned side by side.
    """

    def setUp(self) -> None:
        self.violences = [ViolenceFactory.create(name=name) for name in ("gamma", "alpha", "beta")]

    def test_junk_token_is_rejected_and_names_only_the_client_token(self):
        with self.assertRaises(ValueError) as ctx:
            OrderingOnlyArgumentPagination().paginate_queryset(Violence.objects.all(), ordering="zzz__nope")
        self.assertEqual(str(ctx.exception), "Invalid ordering field: zzz__nope")

    def test_each_token_of_a_comma_joined_ordering_is_checked(self):
        with self.assertRaises(ValueError) as ctx:
            OrderingOnlyArgumentPagination().paginate_queryset(Violence.objects.all(), ordering="name,-zzz__nope")
        self.assertEqual(str(ctx.exception), "Invalid ordering field: zzz__nope")

    def test_a_doubled_direction_prefix_is_rejected(self):
        with self.assertRaises(ValueError) as ctx:
            OrderingOnlyArgumentPagination().paginate_queryset(Violence.objects.all(), ordering="--name")
        self.assertEqual(str(ctx.exception), "Invalid ordering field: -name")
        self.assertNotIn("Choices are", str(ctx.exception))

    def test_valid_token_still_orders(self):
        qs = OrderingOnlyArgumentPagination().paginate_queryset(Violence.objects.all(), ordering="-name")
        self.assertEqual([violence.name for violence in qs], ["gamma", "beta", "alpha"])


class TestNestedListOrderingGuard(HelixTestCase):
    """The THIRD ordering chokepoint.

    A *paginated* nested list is resolved by `FilteredRelationListLoader`, which never calls either
    pagination class: it numbers each parent's children with `Window(order_by=...)` built by
    `_ordering_expressions`. Same guard, same message, or a nested list accepts what its
    top-level counterpart refuses. Pinned next to the other two so they cannot drift.

    End-to-end coverage over GraphQL lives in
    `apps/contrib/tests/test_nested_ordering_allowlist.py`.
    """

    def setUp(self) -> None:
        country = CountryFactory.create()
        event = EventFactory.create()
        entry = EntryFactory.create()
        FigureFactory.create_batch(2, entry=entry, event=event, country=country)

    def test_junk_token_is_rejected_and_names_only_the_client_token(self):
        with self.assertRaises(ValueError) as ctx:
            _ordering_expressions(Figure.objects.all(), "ordering", {"ordering": "-zzz__nope"})
        self.assertEqual(str(ctx.exception), "Invalid ordering field: zzz__nope")

    def test_resolvable_but_not_allowlisted_key_is_rejected(self):
        with self.assertRaises(ValueError) as ctx:
            _ordering_expressions(Figure.objects.all(), "ordering", {"ordering": "unit"})
        self.assertEqual(str(ctx.exception), "Invalid ordering field: unit")

    def test_each_token_of_a_comma_joined_ordering_is_checked(self):
        with self.assertRaises(ValueError) as ctx:
            _ordering_expressions(Figure.objects.all(), "ordering", {"ordering": "role,-unit"})
        self.assertEqual(str(ctx.exception), "Invalid ordering field: unit")

    def test_a_doubled_direction_prefix_is_rejected(self):
        with self.assertRaises(ValueError) as ctx:
            _ordering_expressions(Figure.objects.all(), "ordering", {"ordering": "--created_at"})
        self.assertEqual(str(ctx.exception), "Invalid ordering field: -created_at")
        self.assertNotIn("Choices are", str(ctx.exception))

    def test_allowlisted_key_builds_the_expression_plus_a_pk_tiebreaker(self):
        expressions = _ordering_expressions(Figure.objects.all(), "ordering", {"ordering": "-created_at"})
        self.assertEqual(
            [str(each) for each in expressions], [str(F("created_at").desc(nulls_last=True)), str(F("pk").desc())]
        )

    def test_empty_ordering_needs_no_token_and_falls_back_to_pk(self):
        self.assertEqual(
            [str(each) for each in _ordering_expressions(Figure.objects.all(), "ordering", {})],
            [str(F("pk").asc())],
        )

    def test_the_childs_meta_ordering_is_the_fallback(self):
        """Mirrors the top-level fallback: the model's keys, then a pk tiebreaker.

        A window numbering by pk alone would order a nested list differently from its own
        top-level list over the same model.
        """
        self.assertEqual(
            [str(each) for each in _ordering_expressions(ReportComment.objects.all(), "ordering", {})],
            [str(F("created_at").desc()), str(F("pk").desc())],
        )

    def test_the_querysets_own_ordering_leads_the_window(self):
        """A queryset's `order_by` has no bearing on ROW_NUMBER, so it has to be restated.

        Without this the nested list numbers its rows ignoring the bucket the top-level list
        leads with, and the two routes disagree for the same arguments.
        """
        self.assertEqual(
            [str(each) for each in _ordering_expressions(Figure.objects.order_by("role"), "ordering", {})],
            [str(F("role").asc()), str(F("pk").asc())],
        )
        self.assertEqual(
            [
                str(each)
                for each in _ordering_expressions(Figure.objects.order_by("role"), "ordering", {"ordering": "-created_at"})
            ],
            [str(F("role").asc()), str(F("created_at").desc(nulls_last=True)), str(F("pk").desc())],
        )

    def test_unmapped_model_falls_back_to_resolvability(self):
        self.assertIsNone(get_ordering_allowlist(Violence))
        _ordering_expressions(Violence.objects.all(), "ordering", {"ordering": "name"})
        with self.assertRaises(ValueError) as ctx:
            _ordering_expressions(Violence.objects.all(), "ordering", {"ordering": "zzz__nope"})
        self.assertEqual(str(ctx.exception), "Invalid ordering field: zzz__nope")
