"""The per-model ORDERING_ALLOWLIST applies to nested lists too, end to end over GraphQL.

A *paginated* nested list is resolved by `OneToManyLoader.batch_load_fn`, which builds
`Window(order_by=_ordering_expressions(...))` instead of going through either pagination
class. Until the guard was added there, `crisisList { events(ordering: ..., pageSize: N) }`
took any token the ORM could resolve: junk came back as Django's raw `FieldError` (which
enumerates every column on the model, schema-private ones included) and a real-but-
unallowlisted to-many path such as `countries__iso3` simply worked, so no allowlist entry
could be read as "unreachable".

The four nested `ordering` usages both GraphQL clients actually send —
`report { comments }`, `report { generations }`, `country { summaries }`,
`country { contextualAnalyses }` — are pinned here, because the guard's blast radius is
exactly "every nested list", and a too-narrow allowlist would break them silently.
"""

import json

from apps.report.models import ReportGeneration
from apps.users.enums import USER_ROLE
from utils.factories import (
    ContextualAnalysisFactory,
    CountryFactory,
    CrisisFactory,
    EventFactory,
    ReportCommentFactory,
    ReportFactory,
    SummaryFactory,
)
from utils.tests import HelixGraphQLTestCase, create_user_with_role

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


class TestNestedEventListOrderingIsAllowlisted(HelixGraphQLTestCase):
    """`crisisList { events(ordering:) }` is the nested list with the widest key set."""

    @classmethod
    def setUpTestData(cls):
        cls.countries = [
            CountryFactory.create(idmc_short_name=name, iso3=iso3)
            for name, iso3 in (("Alphaland", "AAA"), ("Betaland", "BBB"), ("Gammaland", "CCC"))
        ]
        cls.crisis = CrisisFactory.create(name="nested-crisis")
        cls.crisis.countries.set(cls.countries)
        cls.events = [EventFactory.create(crisis=cls.crisis, countries=cls.countries) for _ in range(2)]

    def setUp(self) -> None:
        super().setUp()
        self.force_login(create_user_with_role(USER_ROLE.ADMIN.name))

    def _events(self, ordering):
        response = self.query(NESTED_EVENTS_QUERY, variables={"ordering": ordering})
        return json.loads(response.content)

    def assert_rejected(self, ordering, token):
        content = self._events(ordering)
        messages = {error["message"] for error in content["errors"]}
        self.assertEqual(messages, {"Invalid ordering field: %s" % token}, content)

    def assert_accepted(self, ordering):
        content = self._events(ordering)
        self.assertNotIn("errors", content, content)
        payload = content["data"]["crisisList"]["results"][0]["events"]
        ids = [row["id"] for row in payload["results"]]
        # One row per event: a to-many sort key must not fan the parent out inside the page.
        self.assertEqual(sorted(ids), sorted(str(event.id) for event in self.events), payload)
        self.assertEqual(payload["totalCount"], len(self.events), payload)

    def test_junk_token_is_rejected_without_leaking_the_field_list(self):
        for direction in ("", "-"):
            with self.subTest(ordering=direction + "zzz__nope"):
                self.assert_rejected(direction + "zzz__nope", "zzz__nope")

    def test_resolvable_but_not_allowlisted_to_many_token_is_rejected(self):
        # `countries__iso3` orders fine and used to be accepted here only because this path
        # skipped the allowlist. Rejecting it is what makes the token unreachable on every
        # route, which is why `event.Event` needs no `countries__iso3` denormalisation (see
        # apps/contrib/tests/test_to_many_ordering_fanout.py).
        for direction in ("", "-"):
            with self.subTest(ordering=direction + "countries__iso3"):
                self.assert_rejected(direction + "countries__iso3", "countries__iso3")

    def test_each_token_of_a_comma_joined_ordering_is_checked(self):
        self.assert_rejected("name,unit", "unit")

    def test_allowlisted_tokens_still_order(self):
        for token in ("name", "-name", "created_at", "-created_at", "start_date", "id", "-id"):
            with self.subTest(ordering=token):
                self.assert_accepted(token)

    def test_allowlisted_to_many_token_still_orders(self):
        for direction in ("", "-"):
            with self.subTest(ordering=direction + "countries__idmc_short_name"):
                self.assert_accepted(direction + "countries__idmc_short_name")

    def test_ordering_gated_annotation_aliases_still_resolve(self):
        # These exist only because _filtered_qs() forwards `ordering` to EventFilter, so the
        # allowlist check has to run against that filtered queryset, not an earlier one.
        for token in ("entry_count", "-progress", "total_flow_nd_figures", "-total_stock_idp_figures"):
            with self.subTest(ordering=token):
                self.assert_accepted(token)

    def test_no_ordering_is_still_served(self):
        self.assert_accepted("")


class TestClientNestedOrderingUsages(HelixGraphQLTestCase):
    """The only four nested `ordering` arguments helix-client / idmc-website-components send.

    Every one of them is an allowlist entry; if the allowlist is ever narrowed these go red
    before a user does.
    """

    @classmethod
    def setUpTestData(cls):
        cls.report = ReportFactory.create(name="ordering-report")
        cls.comments = ReportCommentFactory.create_batch(3, report=cls.report)
        cls.country = CountryFactory.create(idmc_short_name="Alphaland", iso3="AAA")
        cls.summaries = SummaryFactory.create_batch(3, country=cls.country)
        cls.analyses = ContextualAnalysisFactory.create_batch(3, country=cls.country)

    def setUp(self) -> None:
        super().setUp()
        self.user = create_user_with_role(USER_ROLE.ADMIN.name)
        self.force_login(self.user)
        self.generations = [ReportGeneration.objects.create(report=self.report, created_by=self.user) for _ in range(3)]

    def assert_ordered(self, query, path, ordering, expected_ids):
        response = self.query(query, variables={"ordering": ordering})
        content = json.loads(response.content)
        self.assertNotIn("errors", content, content)
        node = content["data"]
        for key in path:
            node = node[key]
        self.assertEqual([row["id"] for row in node["results"]], expected_ids, content)

    def test_report_comments_ordering_created_at(self):
        query = (
            """
            query MyQuery($ordering: String) {
              report(id: %s) {
                id
                comments(ordering: $ordering, pageSize: 50) { totalCount results { id } }
              }
            }
        """
            % self.report.id
        )
        ascending = [str(comment.id) for comment in sorted(self.comments, key=lambda c: (c.created_at, -c.id))]
        self.assert_ordered(query, ("report", "comments"), "created_at", ascending)
        self.assert_ordered(query, ("report", "comments"), "-created_at", list(reversed(ascending)))

    def test_report_generations_ordering_id(self):
        query = (
            """
            query MyQuery($ordering: String) {
              report(id: %s) {
                id
                generations(ordering: $ordering) { totalCount results { id } }
              }
            }
        """
            % self.report.id
        )
        ascending = [str(generation.id) for generation in sorted(self.generations, key=lambda g: g.id)]
        self.assert_ordered(query, ("report", "generations"), "id", ascending)
        self.assert_ordered(query, ("report", "generations"), "-id", list(reversed(ascending)))

    def test_country_summaries_ordering_created_at(self):
        query = (
            """
            query MyQuery($ordering: String) {
              country(id: %s) {
                id
                summaries(ordering: $ordering, pageSize: 50) { totalCount results { id } }
              }
            }
        """
            % self.country.id
        )
        ascending = [str(summary.id) for summary in sorted(self.summaries, key=lambda s: (s.created_at, -s.id))]
        self.assert_ordered(query, ("country", "summaries"), "created_at", ascending)
        self.assert_ordered(query, ("country", "summaries"), "-created_at", list(reversed(ascending)))

    def test_country_contextual_analyses_ordering_created_at(self):
        query = (
            """
            query MyQuery($ordering: String) {
              country(id: %s) {
                id
                contextualAnalyses(ordering: $ordering, pageSize: 50) { totalCount results { id } }
              }
            }
        """
            % self.country.id
        )
        ascending = [str(analysis.id) for analysis in sorted(self.analyses, key=lambda a: (a.created_at, -a.id))]
        self.assert_ordered(query, ("country", "contextualAnalyses"), "created_at", ascending)
        self.assert_ordered(query, ("country", "contextualAnalyses"), "-created_at", list(reversed(ascending)))
