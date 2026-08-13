"""Ordering a list by a to-many path must not multiply parent rows.

Ordering by an M2M path adds a JOIN, so one parent comes back once per related child,
while `totalCount` -- computed on the filtered queryset *before* the ordering join is
added -- never counts the duplicates. The parent then repeats inside a page and a client
can page past the count.

Each list therefore denormalises the sort key into a per-parent scalar -- a whole-table CTE
on the large lists, a correlated subquery on the small ones, whichever shape is cheaper for
that table -- and aliases the annotation to the ordering token, so `order_by` binds to the
scalar instead of re-traversing the M2M.

The scalar also has to rank the parents the way the JOIN did: ascending, a parent sits at its
alphabetically smallest child; descending, at its greatest. A concatenation of the children
cannot express that -- it ranks every parent by its smallest child in both directions, so
descending reads the smallest child backwards, and a parent whose smallest child is extended by
another parent's child loses to that parent because the separator sorts against the extension.
Cardinality assertions are blind to all of it, so the four `ToManySortKeySequenceMixin` classes
pin the exact id SEQUENCE for every list and every key: both denormalisation shapes (whole-table
CTE, correlated subquery) and both directions of each key, since ascending reduces with Min and
descending with Max and the two arms are written separately per list.

`test_the_fixtures_can_actually_fan_out` is the anti-vacuity guard: it orders through the
raw M2M path with the ORM and asserts the row count really does exceed the parent count,
so a fixture that quietly stopped exercising the bug fails loudly instead of turning the
rest of the file green for free.

Not every to-many path is denormalised: a key no caller can reach carries no fan-out, so it
carries no fix either. `eventList/countries__iso3` is the worked example --
`TestEventCountriesIso3OrderingStaysRejected` pins the rejection that keeps it unreachable,
on both the top-level and the nested route. The general guard is the allowlist registry
test, which fails on any change to the permitted key sets.
"""

import json

from apps.common.utils import EXTERNAL_ARRAY_SEPARATOR
from apps.contact.models import Contact
from apps.contextualupdate.models import ContextualUpdate
from apps.crisis.models import Crisis
from apps.entry.models import Entry
from apps.event.models import Event
from apps.organization.models import Organization
from apps.users.enums import USER_ROLE
from utils.factories import (
    ContactFactory,
    CountryFactory,
    CrisisFactory,
    EntryFactory,
    EventFactory,
    OrganizationFactory,
)
from utils.graphene.ordering import get_ordering_allowlist
from utils.tests import HelixGraphQLTestCase, create_user_with_role

LIST_QUERY = """
    query MyQuery($ordering: String) {
      %s(ordering: $ordering, pageSize: 100) {
        totalCount
        results { id }
      }
    }
"""

# The paginated nested-list route (FilteredRelationListLoader + Window), the other place a sort key
# can reach the ORM.
NESTED_EVENTS_QUERY = """
    query MyQuery($ordering: String) {
      crisisList(pageSize: 10) {
        results {
          id
          events(ordering: $ordering, pageSize: 100) {
            totalCount
            results { id }
          }
        }
      }
    }
"""


class TestToManyOrderingDoesNotFanOut(HelixGraphQLTestCase):
    """One row per parent for every to-many sort key a client can actually send.

    The ordering tokens exercised here are exactly the to-many entries of
    each model's ORDERING_ALLOWLIST -- everything else the allowlist
    rejects before it reaches the ORM.
    """

    @classmethod
    def setUpTestData(cls):
        # Three children per parent: fan-out triples the row, and three (not two) keeps a
        # single accidental DISTINCT-ish dedup from hiding it.
        cls.countries = [
            CountryFactory.create(idmc_short_name=name, iso3=iso3)
            for name, iso3 in (("Alphaland", "AAA"), ("Betaland", "BBB"), ("Gammaland", "CCC"))
        ]
        cls.orgs = [OrganizationFactory.create(name="org-%d" % index) for index in range(3)]

        cls.entries = [EntryFactory.create() for _ in range(2)]
        for entry in cls.entries:
            entry.publishers.set(cls.orgs)

        cls.events = [EventFactory.create(countries=cls.countries) for _ in range(2)]

        cls.crises = [CrisisFactory.create(name="crisis-%d" % index) for index in range(2)]
        for crisis in cls.crises:
            crisis.countries.set(cls.countries)

        for org in cls.orgs:
            org.countries.set(cls.countries)

        # organization= pins the contact to an existing org so ContactFactory's SubFactory
        # does not add organizations the organizationList assertions do not expect.
        cls.contacts = [ContactFactory.create(organization=cls.orgs[0]) for _ in range(2)]
        for contact in cls.contacts:
            contact.countries_of_operation.set(cls.countries)

        cls.contextual_updates = [ContextualUpdate.objects.create(article_title="update-%d" % index) for index in range(2)]
        for update in cls.contextual_updates:
            update.countries.set(cls.countries)
            update.publishers.set(cls.orgs)
            update.sources.set(cls.orgs)

    def setUp(self) -> None:
        super().setUp()
        # ContactFilter returns .none() for a GUEST, so every case runs as ADMIN.
        self.force_login(create_user_with_role(USER_ROLE.ADMIN.name))

    def assert_one_row_per_parent(self, list_field, ordering, expected_ids):
        expected_ids = {str(pk) for pk in expected_ids}
        for direction in ("", "-"):
            with self.subTest(list_field=list_field, ordering=direction + ordering):
                response = self.query(LIST_QUERY % list_field, variables={"ordering": direction + ordering})
                self.assertResponseNoErrors(response)
                payload = json.loads(response.content)["data"][list_field]
                ids = [row["id"] for row in payload["results"]]
                # The bug is precisely "more rows than the count says": assert the returned
                # row COUNT, not just the set of ids.
                self.assertEqual(len(ids), len(expected_ids), payload)
                self.assertEqual(payload["totalCount"], len(expected_ids), payload)
                self.assertEqual(len(ids), len(set(ids)), payload)
                self.assertEqual(set(ids), expected_ids, payload)

    def test_entry_list_by_publishers_name(self):
        self.assert_one_row_per_parent("entryList", "publishers__name", [each.id for each in self.entries])

    def test_event_list_by_countries_idmc_short_name(self):
        self.assert_one_row_per_parent("eventList", "countries__idmc_short_name", [each.id for each in self.events])

    def test_crisis_list_by_countries_idmc_short_name(self):
        self.assert_one_row_per_parent("crisisList", "countries__idmc_short_name", [each.id for each in self.crises])

    def test_organization_list_by_countries_idmc_short_name(self):
        self.assert_one_row_per_parent("organizationList", "countries__idmc_short_name", [each.id for each in self.orgs])

    def test_contact_list_by_countries_of_operation(self):
        self.assert_one_row_per_parent(
            "contactList", "countries_of_operation__idmc_short_name", [each.id for each in self.contacts]
        )

    def test_contextual_update_list_by_each_to_many_sort_key(self):
        expected = [each.id for each in self.contextual_updates]
        for ordering in ("countries__idmc_short_name", "publishers__name", "sources__name"):
            self.assert_one_row_per_parent("contextualUpdateList", ordering, expected)

    def test_the_fixtures_can_actually_fan_out(self):
        """Without the denormalisation these orderings triple the row count.

        Ordering through the raw M2M path is what the filtersets used to do; if this stops
        fanning out, the fixtures no longer reproduce the bug and the assertions above are
        worthless.
        """
        children = len(self.countries)
        cases = [
            (Entry.objects.all(), "publishers__name", len(self.entries), len(self.orgs)),
            (Event.objects.all(), "countries__idmc_short_name", len(self.events), children),
            (Event.objects.all(), "countries__iso3", len(self.events), children),
            (Crisis.objects.all(), "countries__idmc_short_name", len(self.crises), children),
            (Organization.objects.all(), "countries__idmc_short_name", len(self.orgs), children),
            (Contact.objects.all(), "countries_of_operation__idmc_short_name", len(self.contacts), children),
            (ContextualUpdate.objects.all(), "countries__idmc_short_name", len(self.contextual_updates), children),
            (ContextualUpdate.objects.all(), "publishers__name", len(self.contextual_updates), len(self.orgs)),
            (ContextualUpdate.objects.all(), "sources__name", len(self.contextual_updates), len(self.orgs)),
        ]
        for queryset, path, parents, per_parent in cases:
            with self.subTest(model=queryset.model.__name__, path=path):
                rows = len(list(queryset.order_by(path).values_list("id", flat=True)))
                self.assertEqual(rows, parents * per_parent, "%s no longer fans out on %s" % (queryset.model, path))


class TestEventCountriesIso3OrderingStaysRejected(HelixGraphQLTestCase):
    """`eventList` and every nested event list must keep rejecting `countries__iso3`.

    Ordering events by the `countries` M2M path fans one event out into one row per country. No
    denormalisation exists for it, because the token is unreachable: it is absent from
    Event.ORDERING_ALLOWLIST, so all three chokepoints refuse it -- both pagination
    classes for `eventList`, and `_ordering_expressions` (utils/graphene/dataloaders.py) for
    the paginated nested list `crisisList { events(ordering: ...) }`, which was the last route
    that could reach it.

    IF YOU ADD `countries__iso3` TO Event.ORDERING_ALLOWLIST, WRITE THE
    DENORMALISATION FIRST: aggregate the M2M into a per-event scalar and alias that annotation
    to the ordering token, so `order_by` binds to the scalar instead of re-traversing the M2M.
    The `countries__idmc_short_name` blocks in `EventFilter.qs` (apps/event/filters.py) and
    `CrisisFilter.qs` (apps/crisis/filters.py) are the worked examples to copy.
    Widening the allowlist without it makes the event lists return duplicate events inside a
    page and lets a client page past its own totalCount, silently. This test going red IS that
    warning; do not "fix" it by deleting the assertion.

    The same reasoning applies to any *new* to-many token added for `event.Event`.
    """

    @classmethod
    def setUpTestData(cls):
        cls.countries = [
            CountryFactory.create(idmc_short_name=name, iso3=iso3)
            for name, iso3 in (("Alphaland", "AAA"), ("Betaland", "BBB"), ("Gammaland", "CCC"))
        ]
        cls.crisis = CrisisFactory.create(name="iso3-crisis")
        cls.events = [EventFactory.create(crisis=cls.crisis, countries=cls.countries) for _ in range(2)]

    def setUp(self) -> None:
        super().setUp()
        self.force_login(create_user_with_role(USER_ROLE.ADMIN.name))

    def test_countries_iso3_is_not_allowlisted_for_events(self):
        self.assertNotIn("countries__iso3", get_ordering_allowlist(Event))

    def test_event_list_rejects_countries_iso3_ordering(self):
        for direction in ("", "-"):
            with self.subTest(ordering=direction + "countries__iso3"):
                response = self.query(LIST_QUERY % "eventList", variables={"ordering": direction + "countries__iso3"})
                errors = json.loads(response.content)["errors"]
                self.assertEqual([error["message"] for error in errors], ["Invalid ordering field: countries__iso3"])

    def test_nested_event_list_rejects_countries_iso3_ordering(self):
        # The route that used to bypass the allowlist entirely.
        for direction in ("", "-"):
            with self.subTest(ordering=direction + "countries__iso3"):
                response = self.query(NESTED_EVENTS_QUERY, variables={"ordering": direction + "countries__iso3"})
                errors = json.loads(response.content)["errors"]
                self.assertEqual({error["message"] for error in errors}, {"Invalid ordering field: countries__iso3"})

    def test_the_fixtures_can_actually_fan_out(self):
        """Anti-vacuity: the raw M2M ordering the allowlist blocks really does duplicate rows."""
        rows = len(list(Event.objects.order_by("countries__iso3").values_list("id", flat=True)))
        self.assertEqual(rows, len(self.events) * len(self.countries))


# One entry per parent, holding that parent's child names. Every parent but one owns several
# children whose alphabetically first and last differ, because a single-child parent ranks
# identically under all three candidate keys and so discriminates nothing:
#
#   parent  children                    smallest                   greatest      concatenation
#   0       Ecuador, Yemen              Ecuador                    Yemen         "Ecuador; Yemen"
#   1       Congo, Zimbabwe             Congo                      Zimbabwe      "Congo; Zimbabwe"
#   2       Guinea, Honduras            Guinea                     Honduras      "Guinea; Honduras"
#   3       Congo Democratic Republic   Congo Democratic Republic  (same)        "Congo Democratic Republic"
#
# Parent 3's only child extends parent 1's smallest child, so ascending the concatenation ranks
# parent 3 first -- past the shared "Congo" parent 1's concatenation carries on into "Zimbabwe",
# which loses to "Democratic" -- while the smallest child ranks parent 1 first, "Congo" being a
# prefix of parent 3's child: the ascending discriminator.
# Parent 1 owns both the greatest child overall and the smallest, so ranking by the greatest child
# is neither the ascending order reversed nor the concatenation reversed: the descending one.
#
# This tuple's order is also the parents' CREATION order, hence their pk order, and it is neither
# expected sequence: a sort key that stops discriminating falls back to the pk tiebreaker, so
# expectations that happened to match pk order would pass against no sort key at all.
TO_MANY_SORT_GROUPS = (
    ("Ecuador", "Yemen"),
    ("Congo", "Zimbabwe"),
    ("Guinea", "Honduras"),
    ("Congo Democratic Republic",),
)

# Indices into TO_MANY_SORT_GROUPS: by smallest child ascending, by greatest child descending.
ASCENDING_PARENTS = (1, 3, 0, 2)
DESCENDING_PARENTS = (1, 0, 2, 3)


class ToManySortKeySequenceMixin:
    """Sequence assertions shared by the CTE-backed and the Subquery-backed lists.

    Both directions are asserted as an exact id list rather than a set: the failure this file
    guards against keeps every parent exactly once and only moves it.
    """

    def setUp(self) -> None:
        super().setUp()
        # ContactFilter returns .none() for a GUEST, so every case runs as ADMIN.
        self.force_login(create_user_with_role(USER_ROLE.ADMIN.name))

    @classmethod
    def create_sort_key_countries(cls):
        """A country per distinct name in TO_MANY_SORT_GROUPS, keyed by that name."""
        return {
            name: CountryFactory.create(idmc_short_name=name)
            for name in sorted({name for group in TO_MANY_SORT_GROUPS for name in group})
        }

    @classmethod
    def create_sort_key_organizations(cls):
        """An organization per distinct name in TO_MANY_SORT_GROUPS, keyed by that name."""
        return {
            name: OrganizationFactory.create(name=name)
            for name in sorted({name for group in TO_MANY_SORT_GROUPS for name in group})
        }

    @classmethod
    def children_of(cls, children_by_name, index):
        return [children_by_name[name] for name in TO_MANY_SORT_GROUPS[index]]

    def assert_id_sequence(self, list_field, ordering, expected_parents):
        response = self.query(LIST_QUERY % list_field, variables={"ordering": ordering})
        self.assertResponseNoErrors(response)
        payload = json.loads(response.content)["data"][list_field]
        expected_ids = [str(parent.id) for parent in expected_parents]
        self.assertEqual([row["id"] for row in payload["results"]], expected_ids, payload)
        self.assertEqual(payload["totalCount"], len(expected_ids), payload)

    def assert_ascends_by_smallest_child(self, list_field, ordering, parents):
        self.assert_id_sequence(list_field, ordering, [parents[index] for index in ASCENDING_PARENTS])

    def assert_descends_by_greatest_child(self, list_field, ordering, parents):
        self.assert_id_sequence(list_field, "-" + ordering, [parents[index] for index in DESCENDING_PARENTS])

    def test_the_fixture_discriminates_between_the_candidate_keys(self):
        """Anti-vacuity: smallest child, greatest child and concatenation rank these parents differently.

        The expected sequences are only worth asserting while a concatenated key would produce
        different ones; a fixture edit that flattens the three orders into one turns both sequence
        assertions green against the bug.

        Neither sequence may be the parents' pk order either. TO_MANY_SORT_GROUPS is iterated to
        create them, so its index IS the pk order: an expectation equal to it -- or to its reverse
        -- is reproduced by the pk tiebreaker alone, i.e. by a sort key that discriminates nothing.
        """
        indices = range(len(TO_MANY_SORT_GROUPS))
        pk_order = tuple(indices)
        self.assertNotEqual(ASCENDING_PARENTS, pk_order)
        self.assertNotEqual(DESCENDING_PARENTS, pk_order)
        self.assertNotEqual(ASCENDING_PARENTS, tuple(reversed(pk_order)))
        self.assertNotEqual(DESCENDING_PARENTS, tuple(reversed(pk_order)))

        concatenations = [EXTERNAL_ARRAY_SEPARATOR.join(sorted(group)) for group in TO_MANY_SORT_GROUPS]
        by_smallest = tuple(sorted(indices, key=lambda index: min(TO_MANY_SORT_GROUPS[index])))
        by_greatest_desc = tuple(sorted(indices, key=lambda index: max(TO_MANY_SORT_GROUPS[index]), reverse=True))
        by_concatenation = tuple(sorted(indices, key=lambda index: concatenations[index]))

        self.assertEqual(by_smallest, ASCENDING_PARENTS)
        self.assertEqual(by_greatest_desc, DESCENDING_PARENTS)
        self.assertNotEqual(by_concatenation, ASCENDING_PARENTS)
        self.assertNotEqual(tuple(reversed(by_concatenation)), DESCENDING_PARENTS)
        # A key that stays on the smallest child in both directions is the other near-miss.
        self.assertNotEqual(tuple(reversed(by_smallest)), DESCENDING_PARENTS)


class TestToManyOrderingSequenceThroughCte(ToManySortKeySequenceMixin, HelixGraphQLTestCase):
    """`eventList` and `crisisList` rank each parent at its extreme country, not at a concatenation.

    Both denormalise `countries__idmc_short_name` through a whole-table django-cte CTE joined back
    by id -- the shape the large lists use -- so they share one code path, distinct from the
    correlated subquery `TestToManyOrderingSequenceThroughSubquery` covers.

    The sequences pinned here are the JOIN's: ascending, a parent sits where its alphabetically
    smallest country sits; descending, where its greatest does. Both fail against a key that
    concatenates the countries, which ascending misranks a parent whose smallest country another
    parent's country extends, and descending reads the smallest country backwards.
    """

    @classmethod
    def setUpTestData(cls):
        cls.countries = cls.create_sort_key_countries()
        cls.events = [
            EventFactory.create(countries=cls.children_of(cls.countries, index)) for index in range(len(TO_MANY_SORT_GROUPS))
        ]
        cls.crises = []
        for index in range(len(TO_MANY_SORT_GROUPS)):
            crisis = CrisisFactory.create(name="crisis-%d" % index)
            crisis.countries.set(cls.children_of(cls.countries, index))
            cls.crises.append(crisis)

    def test_event_list_ascends_by_smallest_country_name(self):
        self.assert_ascends_by_smallest_child("eventList", "countries__idmc_short_name", self.events)

    def test_event_list_descends_by_greatest_country_name(self):
        self.assert_descends_by_greatest_child("eventList", "countries__idmc_short_name", self.events)

    def test_crisis_list_ascends_by_smallest_country_name(self):
        self.assert_ascends_by_smallest_child("crisisList", "countries__idmc_short_name", self.crises)

    def test_crisis_list_descends_by_greatest_country_name(self):
        self.assert_descends_by_greatest_child("crisisList", "countries__idmc_short_name", self.crises)


class TestToManyOrderingSequenceThroughSubquery(ToManySortKeySequenceMixin, HelixGraphQLTestCase):
    """`organizationList` and `contactList` pin the same sequences on the correlated-subquery shape.

    These lists denormalise per row with a correlated subquery instead of a CTE, a separate code
    path that has to agree with the CTE one: the sort key a client sends is the same, so the order
    it produces must be too.
    """

    @classmethod
    def setUpTestData(cls):
        cls.countries = cls.create_sort_key_countries()
        cls.organizations = [OrganizationFactory.create(name="org-%d" % index) for index in range(len(TO_MANY_SORT_GROUPS))]
        for index, organization in enumerate(cls.organizations):
            organization.countries.set(cls.children_of(cls.countries, index))

        # organization= pins the contact to an existing org so ContactFactory's SubFactory does not
        # add organizations the organizationList sequence does not expect.
        cls.contacts = [ContactFactory.create(organization=cls.organizations[0]) for _ in range(len(TO_MANY_SORT_GROUPS))]
        for index, contact in enumerate(cls.contacts):
            contact.countries_of_operation.set(cls.children_of(cls.countries, index))

    def test_organization_list_ascends_by_smallest_country_name(self):
        self.assert_ascends_by_smallest_child("organizationList", "countries__idmc_short_name", self.organizations)

    def test_organization_list_descends_by_greatest_country_name(self):
        self.assert_descends_by_greatest_child("organizationList", "countries__idmc_short_name", self.organizations)

    def test_contact_list_ascends_by_smallest_country_of_operation_name(self):
        self.assert_ascends_by_smallest_child("contactList", "countries_of_operation__idmc_short_name", self.contacts)

    def test_contact_list_descends_by_greatest_country_of_operation_name(self):
        self.assert_descends_by_greatest_child("contactList", "countries_of_operation__idmc_short_name", self.contacts)


class TestEntryToManyOrderingSequence(ToManySortKeySequenceMixin, HelixGraphQLTestCase):
    """`entryList` ranks each entry at its extreme publisher, not at a concatenation.

    `publishers__name` (apps/extraction/filters.py) denormalises through the same whole-table CTE
    the event/crisis lists use, and picks Min or Max by direction. Only these sequences separate
    that from a key pinned to one aggregate in both directions, which returns the ascending order
    reversed -- a shape the cardinality assertions above cannot see.

    A separate class from the event/crisis one because the publisher organizations are named after
    the sort-key groups, which `organizationList`'s own sequence assertions would then include.
    """

    @classmethod
    def setUpTestData(cls):
        cls.organizations = cls.create_sort_key_organizations()
        cls.entries = []
        for index in range(len(TO_MANY_SORT_GROUPS)):
            entry = EntryFactory.create()
            entry.publishers.set(cls.children_of(cls.organizations, index))
            cls.entries.append(entry)

    def test_entry_list_ascends_by_smallest_publisher_name(self):
        self.assert_ascends_by_smallest_child("entryList", "publishers__name", self.entries)

    def test_entry_list_descends_by_greatest_publisher_name(self):
        self.assert_descends_by_greatest_child("entryList", "publishers__name", self.entries)


class TestContextualUpdateToManyOrderingSequence(ToManySortKeySequenceMixin, HelixGraphQLTestCase):
    """All three `contextualUpdateList` to-many sort keys, on the correlated-subquery shape.

    `countries__idmc_short_name`, `publishers__name` and `sources__name`
    (apps/contextualupdate/filters.py) each get their own per-row subquery, so each direction of
    each key is its own arm; the same group is attached to all three relations per update, so one
    pair of expected sequences pins all six.
    """

    TOKENS = ("countries__idmc_short_name", "publishers__name", "sources__name")

    @classmethod
    def setUpTestData(cls):
        cls.countries = cls.create_sort_key_countries()
        cls.organizations = cls.create_sort_key_organizations()
        cls.updates = []
        for index in range(len(TO_MANY_SORT_GROUPS)):
            update = ContextualUpdate.objects.create(article_title="update-%d" % index)
            update.countries.set(cls.children_of(cls.countries, index))
            update.publishers.set(cls.children_of(cls.organizations, index))
            update.sources.set(cls.children_of(cls.organizations, index))
            cls.updates.append(update)

    def test_contextual_update_list_ascends_by_smallest_related_name(self):
        for token in self.TOKENS:
            with self.subTest(ordering=token):
                self.assert_ascends_by_smallest_child("contextualUpdateList", token, self.updates)

    def test_contextual_update_list_descends_by_greatest_related_name(self):
        for token in self.TOKENS:
            with self.subTest(ordering="-" + token):
                self.assert_descends_by_greatest_child("contextualUpdateList", token, self.updates)
