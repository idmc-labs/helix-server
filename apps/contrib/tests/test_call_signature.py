from django.test import SimpleTestCase

from utils.graphene.dataloaders import call_signature
from utils.graphene.pagination import OrderingOnlyArgumentPagination, PageGraphqlPaginationWithoutCount


class TestCallSignature(SimpleTestCase):
    """`call_signature` decides whether two nested-list resolutions share a loader instance.

    A `FilteredRelationLoader` holds one argument set for its whole batch and caches promises by
    parent id alone, so a signature that collides across two different argument sets serves one
    field's rows to the other. `repr()` cannot key this on its own: it is dict-insertion-ordered,
    set-iteration-ordered, and prints `1`, `True` and `"1"` in ways that do not separate them.
    """

    def signatures_differ(self, left, right, message):
        self.assertNotEqual(call_signature(left), call_signature(right), message)

    def test_dict_key_order_is_not_part_of_the_signature(self):
        """The same filters built in a different order must reuse the loader, not double it.

        `filter_kwargs` is assembled from a GraphQL argument dict, whose key order follows the
        query text. Two clients asking for the same filters with the fields transposed otherwise
        get two loader instances and two batches of identical queries.
        """
        self.assertEqual(
            call_signature({"filter_kwargs": {"a": 1, "b": 2}}),
            call_signature({"filter_kwargs": {"b": 2, "a": 1}}),
        )

    def test_nested_dict_key_order_is_not_part_of_the_signature(self):
        # Filter kwargs nest (a filterset's data holds lists of dicts), so the normalisation has
        # to recurse rather than sort only the top level.
        self.assertEqual(
            call_signature({"filter_kwargs": {"outer": {"a": 1, "b": 2}}}),
            call_signature({"filter_kwargs": {"outer": {"b": 2, "a": 1}}}),
        )

    def test_set_order_is_not_part_of_the_signature(self):
        """Set iteration order is a hash-table artefact, not a filter difference.

        The members collide in a small set's table (`1` and `9` both want slot 1), which is what
        makes insertion order observable at all -- two non-colliding members iterate in slot order
        whichever way they went in, so they would agree even without normalisation.
        """
        self.assertNotEqual(repr({1, 9}), repr({9, 1}), "picked members that do not expose set order")
        self.assertEqual(
            call_signature({"filter_kwargs": {"x": {1, 9}}}),
            call_signature({"filter_kwargs": {"x": {9, 1}}}),
        )

    def test_list_order_is_part_of_the_signature(self):
        """A list is ordered data, so reordering it is a different call.

        `ordering` arrives as a comma-joined string and id lists feed `__in`, but the loader
        cannot know which lists are order-carrying. Sorting them would merge two calls whose
        argument really differs.
        """
        self.signatures_differ(
            {"filter_kwargs": {"x": [1, 2]}},
            {"filter_kwargs": {"x": [2, 1]}},
            "list order was normalised away",
        )

    def test_a_list_and_a_set_of_the_same_members_differ(self):
        self.signatures_differ(
            {"filter_kwargs": {"x": [1, 2]}},
            {"filter_kwargs": {"x": {1, 2}}},
            "a list and a set must not produce the same signature",
        )

    def test_int_str_and_bool_are_distinguished(self):
        """`1`, `"1"` and `True` filter differently, so they must not collide.

        Django coerces all three for a query, but not identically -- `is_active=True` and
        `is_active=1` are the same filter while `id="1"` and `id=1` reach different lookups, and
        `True == 1` in Python means an untyped normalisation maps them to one string.
        """
        as_int = call_signature({"filter_kwargs": {"x": 1}})
        as_str = call_signature({"filter_kwargs": {"x": "1"}})
        as_bool = call_signature({"filter_kwargs": {"x": True}})
        self.assertEqual(len({as_int, as_str, as_bool}), 3, "int, str and bool collided")

    def test_a_class_value_is_distinguished_by_module_and_qualname(self):
        """`filterset_class` is a class object, and two filtersets may share a name.

        A class's default `repr` embeds its module, but a filterset's identity has to survive
        whatever `repr` the metaclass defines, and same-named classes from different apps
        (`EventFilter` in several modules) must stay apart.
        """

        class Alpha:
            pass

        class Beta:
            pass

        self.signatures_differ(
            {"filterset_class": Alpha},
            {"filterset_class": Beta},
            "two distinct filterset classes shared a signature",
        )
        self.assertEqual(
            call_signature({"filterset_class": Alpha}),
            call_signature({"filterset_class": Alpha}),
        )

    def test_same_named_classes_from_different_modules_are_distinguished(self):
        # Build the collision the qualname alone would not catch: identical `__name__`, so only
        # the module (or qualname path) separates them.
        alpha = type("SameName", (), {"__module__": "apps.alpha.filters"})
        beta = type("SameName", (), {"__module__": "apps.beta.filters"})
        self.assertEqual(alpha.__name__, beta.__name__)
        self.signatures_differ(
            {"filterset_class": alpha},
            {"filterset_class": beta},
            "same-named filtersets from different modules shared a signature",
        )

    def test_a_class_is_not_confused_with_its_name(self):
        class Gamma:
            pass

        self.signatures_differ(
            {"filterset_class": Gamma},
            {"filterset_class": f"{Gamma.__module__}.{Gamma.__qualname__}"},
            "a class and the string naming it shared a signature",
        )

    def test_request_is_excluded_from_the_signature(self):
        """A per-request object must not enter the key, or the registry never hits.

        `request` is fixed for the lifetime of the `GQLContext` that owns the loader registry, so
        it carries no information here -- but it has no stable `repr`, so including it would give
        every resolution its own loader and defeat batching entirely.
        """

        class Request:
            def __repr__(self):
                return f"<Request {id(self)}>"

        self.assertEqual(
            call_signature({"parent": "Country", "request": Request()}),
            call_signature({"parent": "Country", "request": Request()}),
        )
        self.assertEqual(
            call_signature({"parent": "Country", "request": Request()}),
            call_signature({"parent": "Country"}),
        )

    def test_pagination_is_reduced_to_its_class(self):
        """Two instances of one pagination class are one call; two classes are not.

        A pagination instance belongs to a field definition and has no stable `repr`, so keying on
        the instance would give each field its own loader. Its class still matters: it decides
        whether the paginated or the whole-relation batch path runs.
        """
        one = OrderingOnlyArgumentPagination()
        another = OrderingOnlyArgumentPagination()
        self.assertIsNot(one, another)
        self.assertEqual(
            call_signature({"pagination": one}),
            call_signature({"pagination": another}),
        )
        self.signatures_differ(
            {"pagination": one},
            {"pagination": PageGraphqlPaginationWithoutCount()},
            "two pagination classes shared a signature",
        )

    def test_a_signature_is_a_hex_digest(self):
        # The result is used as a registry key fragment joined with `_`, so it must be a plain
        # token: a raw repr would carry separators and unbounded length into the key.
        signature = call_signature({"filter_kwargs": {"x": [1, "two", None]}})
        self.assertRegex(signature, r"^[0-9a-f]{40}$")

    def test_differing_arguments_do_not_collide(self):
        # A sweep over the argument shapes a real call carries: every one must key distinctly.
        distinct = [
            {},
            {"parent": "Country"},
            {"parent": "Event"},
            {"parent": "Country", "related_name": "events"},
            {"parent": "Country", "related_name": "figures"},
            {"parent": "Country", "accessor": "events"},
            {"filter_kwargs": {}},
            {"filter_kwargs": None},
            {"filter_kwargs": {"x": None}},
            {"filter_kwargs": {"x": ""}},
            {"filter_kwargs": {"x": 0}},
            {"filter_kwargs": {"x": False}},
            {"filter_kwargs": {"x": [1]}},
            {"filter_kwargs": {"x": [1, 2]}},
            {"filter_kwargs": {"x": 1, "y": 2}},
            {"filter_kwargs": {"x": 1}, "y": 2},
        ]
        signatures = {call_signature(params): params for params in distinct}
        self.assertEqual(len(signatures), len(distinct), f"a signature collided: {signatures}")
