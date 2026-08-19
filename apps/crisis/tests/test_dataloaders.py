import json
from datetime import date

from django.db import connection
from django.test.utils import CaptureQueriesContext

from apps.crisis.models import Crisis
from apps.entry.models import Figure
from apps.users.enums import USER_ROLE
from utils.factories import (
    CountryFactory,
    CrisisFactory,
    EntryFactory,
    EventFactory,
    FigureFactory,
    OrganizationFactory,
)
from utils.tests import HelixGraphQLTestCase, create_user_with_role


class TestGenericDataLoaders(HelixGraphQLTestCase):
    """Guards the generic ``utils.graphene.dataloaders`` FilteredRelationListLoader / FilteredRelationCountLoader that back
    every ``DjangoPaginatedListObjectField`` exposed under a list path.

    Covers the engine's code-path matrix:
      - FilteredRelationListLoader python-group path  (unpaginated reverse-M2M: figure.sources)
      - FilteredRelationListLoader window-CTE path    (paginated reverse-FK: crisis.events(pageSize:N))
      - FilteredRelationCountLoader grouped-count path     (crisis.events.totalCount)
      - childless parent -> empty results / count 0 (no crash)
      - constant (non-N+1) query count: the per-parent overhead must stay flat as the number
        of parent rows grows (the whole point of batching these loaders).
    """

    def setUp(self) -> None:
        self.admin = create_user_with_role(USER_ROLE.ADMIN.name)

        # --- M2M fixture: 2 figures, each with its own 2 source organizations ---
        # sources is Figure.sources -> Organization (reverse_related_name="sourced_figures").
        self.entry = EntryFactory.create()
        self.figure_event = EventFactory.create()

        self.org_a1 = OrganizationFactory.create()
        self.org_a2 = OrganizationFactory.create()
        self.org_b1 = OrganizationFactory.create()
        self.org_b2 = OrganizationFactory.create()

        self.figure_a = FigureFactory.create(entry=self.entry, event=self.figure_event)
        self.figure_b = FigureFactory.create(entry=self.entry, event=self.figure_event)
        self.figure_a.sources.add(self.org_a1, self.org_a2)
        self.figure_b.sources.add(self.org_b1, self.org_b2)
        # A childless figure: no sources at all -> must resolve to an empty list, not crash.
        self.figure_c = FigureFactory.create(entry=self.entry, event=self.figure_event)

        # --- reverse-FK fixture: a crisis with 3 events (Event.crisis related_name="events") ---
        self.crisis = CrisisFactory.create()
        self.events = EventFactory.create_batch(3, crisis=self.crisis)
        # A childless crisis: no events -> event list empty + totalCount 0.
        self.empty_crisis = CrisisFactory.create()

        self.force_login(self.admin)

    def _run(self, query, variables=None):
        response = self.query(query, variables=variables)
        self.assertResponseNoErrors(response)
        return json.loads(response.content)["data"]

    def test_unpaginated_reverse_m2m_sources(self) -> None:
        # FilteredRelationListLoader python-group path: figure.sources has no pageSize param, so the field
        # returns the FULL source set per figure (just ordered). Assert each figure gets exactly
        # its own sources and the childless figure gets an empty list.
        query = """
            query FigureSources {
              figureList(ordering: "id") {
                results {
                  id
                  sources {
                    results { id }
                  }
                }
              }
            }
        """
        data = self._run(query)
        results = data["figureList"]["results"]
        by_id = {r["id"]: {s["id"] for s in r["sources"]["results"]} for r in results}

        self.assertEqual(
            by_id[str(self.figure_a.id)],
            {str(self.org_a1.id), str(self.org_a2.id)},
        )
        self.assertEqual(
            by_id[str(self.figure_b.id)],
            {str(self.org_b1.id), str(self.org_b2.id)},
        )
        # Childless figure: empty source set, no leakage from siblings.
        self.assertEqual(by_id[str(self.figure_c.id)], set())

    def test_paginated_reverse_fk_events_page(self) -> None:
        # FilteredRelationListLoader window-CTE path: crisis.events declares pageSize. Default ordering is
        # empty -> _ordering_expressions falls back to (pk ASC), so page 1 of size 2 is the two
        # lowest-pk events. Assert we get exactly the requested page and the count is the real
        # related total (not the page size).
        query = """
            query CrisisEvents($pageSize: Int!) {
              crisisList(ordering: "id") {
                results {
                  id
                  events(pageSize: $pageSize) {
                    totalCount
                    results { id }
                  }
                }
              }
            }
        """
        data = self._run(query, variables={"pageSize": 2})
        results = {r["id"]: r for r in data["crisisList"]["results"]}

        crisis_node = results[str(self.crisis.id)]
        page_ids = [e["id"] for e in crisis_node["events"]["results"]]
        expected_first_two = [str(e.id) for e in sorted(self.events, key=lambda e: e.id)[:2]]

        # Window-CTE returns exactly one page (page_size rows) per parent...
        self.assertEqual(page_ids, expected_first_two)
        # ...while FilteredRelationCountLoader reports the full related total, independent of the page slice.
        self.assertEqual(crisis_node["events"]["totalCount"], 3)

        # Childless crisis: empty page, count 0, no crash.
        empty_node = results[str(self.empty_crisis.id)]
        self.assertEqual(empty_node["events"]["results"], [])
        self.assertEqual(empty_node["events"]["totalCount"], 0)

    def test_paginated_second_page_is_disjoint(self) -> None:
        # Window numbering must page correctly: page 2 (size 2) of 3 events returns the single
        # remaining (highest-pk) event and never overlaps page 1.
        query = """
            query CrisisEvents($pageSize: Int!, $page: Int!) {
              crisisList(ordering: "id") {
                results {
                  id
                  events(pageSize: $pageSize, page: $page) {
                    totalCount
                    results { id }
                  }
                }
              }
            }
        """
        sorted_ids = [str(e.id) for e in sorted(self.events, key=lambda e: e.id)]

        page1 = self._run(query, variables={"pageSize": 2, "page": 1})
        page2 = self._run(query, variables={"pageSize": 2, "page": 2})

        def events_for(data, crisis_id):
            for r in data["crisisList"]["results"]:
                if r["id"] == crisis_id:
                    return [e["id"] for e in r["events"]["results"]]
            raise AssertionError("crisis not found")

        p1_ids = events_for(page1, str(self.crisis.id))
        p2_ids = events_for(page2, str(self.crisis.id))

        self.assertEqual(p1_ids, sorted_ids[:2])
        self.assertEqual(p2_ids, sorted_ids[2:])
        # No row appears on two pages, union covers everything.
        self.assertEqual(set(p1_ids) & set(p2_ids), set())
        self.assertEqual(set(p1_ids) | set(p2_ids), set(sorted_ids))

    def test_nested_list_query_count_is_flat(self) -> None:
        # The batching contract: resolving the nested list+count for N parents must NOT issue
        # per-parent queries. The exact total query count of the GraphQL pipeline is brittle, so
        # instead we assert it does NOT scale with the number of parent crises: capture the count
        # with a single events-bearing crisis present, then add two more (each with its own
        # events) and capture again. Because FilteredRelationListLoader / FilteredRelationCountLoader batch every parent key
        # into a single query each, the two counts must be EQUAL. An N+1 regression would make the
        # 3-crisis count strictly larger than the 1-crisis count.
        #
        # NOTE: this test stands on its own fixture (it does not use the setUp crises) so the
        # 1-vs-3 parent comparison is exact.
        Crisis.objects.all().delete()  # drop setUp's crises; rebuild a controlled parent set
        query = """
            query CrisisEvents {
              crisisList(ordering: "id") {
                results {
                  id
                  events(pageSize: 2) {
                    totalCount
                    results { id }
                  }
                }
              }
            }
        """
        crisis1 = CrisisFactory.create()
        EventFactory.create_batch(3, crisis=crisis1)

        with CaptureQueriesContext(connection) as ctx_one:
            data_one = self._run(query)
        single_parent_queries = len(ctx_one.captured_queries)
        self.assertEqual(len(data_one["crisisList"]["results"]), 1)

        # Two more events-bearing crises, so the parent fan-out really grows.
        crisis2 = CrisisFactory.create()
        crisis3 = CrisisFactory.create()
        EventFactory.create_batch(3, crisis=crisis2)
        EventFactory.create_batch(3, crisis=crisis3)

        with CaptureQueriesContext(connection) as ctx_many:
            data_many = self._run(query)
        multi_parent_queries = len(ctx_many.captured_queries)
        self.assertEqual(len(data_many["crisisList"]["results"]), 3)

        self.assertEqual(
            single_parent_queries,
            multi_parent_queries,
            "Nested events/count resolution scales with the number of parent crises "
            f"(N+1 regression): {single_parent_queries} query(s) for 1 crisis vs "
            f"{multi_parent_queries} for 3.",
        )

    def test_aliased_page_sizes_each_get_their_own_page(self) -> None:
        # Two aliases of one field are two resolutions with different arguments. A loader
        # resolves its batch with one argument set and caches promises by parent id, so the
        # aliases must not share an instance.
        query = """
            query CrisisEventPages {
              crisisList(ordering: "id") {
                results {
                  id
                  small: events(pageSize: 1) { totalCount results { id } }
                  big: events(pageSize: 3) { totalCount results { id } }
                }
              }
            }
        """
        data = self._run(query)
        node = next(r for r in data["crisisList"]["results"] if r["id"] == str(self.crisis.id))

        self.assertEqual(len(node["small"]["results"]), 1)
        self.assertEqual(len(node["big"]["results"]), 3)
        # Both aliases count the same (unpaged) related set.
        self.assertEqual(node["small"]["totalCount"], 3)
        self.assertEqual(node["big"]["totalCount"], 3)

    def test_filtered_alias_does_not_narrow_its_unfiltered_sibling(self) -> None:
        # Own crisis, so the event types under it are exactly these two.
        Crisis.objects.all().delete()
        crisis = CrisisFactory.create()
        conflict = EventFactory.create(crisis=crisis, event_type=Crisis.CRISIS_TYPE.CONFLICT)
        disaster = EventFactory.create(crisis=crisis, event_type=Crisis.CRISIS_TYPE.DISASTER)
        query = """
            query CrisisEventFilters {
              crisisList(ordering: "id") {
                results {
                  id
                  everything: events(pageSize: 50) { totalCount results { id } }
                  conflicts: events(pageSize: 50, filters: { eventTypes: ["CONFLICT"] }) {
                    totalCount
                    results { id }
                  }
                }
              }
            }
        """
        data = self._run(query)
        node = next(r for r in data["crisisList"]["results"] if r["id"] == str(crisis.id))

        everything = {e["id"] for e in node["everything"]["results"]}
        conflicts = {e["id"] for e in node["conflicts"]["results"]}

        self.assertEqual(everything, {str(conflict.id), str(disaster.id)})
        self.assertEqual(node["everything"]["totalCount"], 2)
        self.assertEqual(conflicts, {str(conflict.id)})
        self.assertEqual(node["conflicts"]["totalCount"], 1)

    def test_aliased_roots_do_not_leak_into_each_other(self) -> None:
        # Same nested field under two aliased top-level lists: separate argument sets again.
        query = """
            query TwoCrisisRoots {
              first: crisisList(ordering: "id") {
                results { id events(pageSize: 1) { results { id } } }
              }
              second: crisisList(ordering: "id") {
                results { id events(pageSize: 3) { results { id } } }
              }
            }
        """
        data = self._run(query)
        first = next(r for r in data["first"]["results"] if r["id"] == str(self.crisis.id))
        second = next(r for r in data["second"]["results"] if r["id"] == str(self.crisis.id))

        self.assertEqual(len(first["events"]["results"]), 1)
        self.assertEqual(len(second["events"]["results"]), 3)

    def _paged_and_count_queries(self, captured):
        # The window-CTE page query and the grouped-count query the two loaders emit.
        paged = [q for q in captured if "ROW_NUMBER()" in q["sql"]]
        counts = [q for q in captured if 'COUNT(*) AS "c"' in q["sql"]]
        return paged, counts

    def test_one_query_per_argument_set_across_all_parents(self) -> None:
        # Batching contract: every parent of one argument set shares a single page query and a
        # single count query, and a second page size adds one page query, not one per parent.
        Crisis.objects.all().delete()
        for _ in range(4):
            EventFactory.create_batch(3, crisis=CrisisFactory.create())

        one_arg_set = """
            query OneArgSet {
              crisisList(pageSize: 50, ordering: "id") {
                results { id events(pageSize: 5) { totalCount results { id } } }
              }
            }
        """
        with CaptureQueriesContext(connection) as ctx:
            data = self._run(one_arg_set)
        self.assertEqual(len(data["crisisList"]["results"]), 4)
        paged, counts = self._paged_and_count_queries(ctx.captured_queries)
        self.assertEqual(len(paged), 1, [q["sql"] for q in paged])
        self.assertEqual(len(counts), 1, [q["sql"] for q in counts])

        two_arg_sets = """
            query TwoArgSets {
              crisisList(pageSize: 50, ordering: "id") {
                results {
                  id
                  small: events(pageSize: 1) { totalCount results { id } }
                  big: events(pageSize: 5) { totalCount results { id } }
                }
              }
            }
        """
        with CaptureQueriesContext(connection) as ctx:
            self._run(two_arg_sets)
        paged, counts = self._paged_and_count_queries(ctx.captured_queries)
        self.assertEqual(len(paged), 2, [q["sql"] for q in paged])
        # A total is pagination-independent, so both aliases are counted by one loader.
        self.assertEqual(len(counts), 1, [q["sql"] for q in counts])

    def test_nested_list_ordered_by_gated_figure_count_annotation(self) -> None:
        # Regression guard: a nested paginated list ordered by a GATED figure-count annotation
        # (total_stock_idp_figures) must not FieldError. The annotation is added only when the
        # ordering references it, so FilteredRelationListLoader must forward `ordering` into the entity
        # filterset (mirroring the top-level path). Before the fix this raised
        # "Cannot resolve keyword 'total_stock_idp_figures'" -> HTTP 500.
        crisis = CrisisFactory.create()
        hi = EventFactory.create(crisis=crisis)
        lo = EventFactory.create(crisis=crisis)
        entry = EntryFactory.create()
        for event, total in ((hi, 500), (lo, 100)):
            FigureFactory.create(
                entry=entry,
                event=event,
                category=Figure.FIGURE_CATEGORY_TYPES.IDPS,
                role=Figure.ROLE.RECOMMENDED,
                total_figures=total,
                end_date=date(2022, 1, 1),  # reference_date = max(end_date); stock counts this figure
            )
        query = """
            query CrisisEventsOrdered {
              crisisList(ordering: "id") {
                results {
                  id
                  events(ordering: "-totalStockIdpFigures", pageSize: 5) {
                    results { id totalStockIdpFigures }
                  }
                }
              }
            }
        """
        data = self._run(query)  # _run asserts no GraphQL errors
        node = next(r for r in data["crisisList"]["results"] if r["id"] == str(crisis.id))
        results = node["events"]["results"]
        # ordered by IDP count desc, and the annotation value is returned (not null)
        self.assertEqual([e["id"] for e in results], [str(hi.id), str(lo.id)])
        vals = {e["id"]: e["totalStockIdpFigures"] for e in results}
        self.assertEqual(vals[str(hi.id)], 500)
        self.assertEqual(vals[str(lo.id)], 100)


class TestNestedListTotalCountGating(HelixGraphQLTestCase):
    """The count of a nested paginated list is resolved only for documents that select it.

    ``totalCount`` is the GraphQL name of ``CustomDjangoListObjectType.count``; a
    document reaches it directly, through an alias, or through a fragment, and each
    form must yield the same total as the unbatched relation count. A document that
    never names it must not pay for the grouped-count query.
    """

    def setUp(self) -> None:
        self.admin = create_user_with_role(USER_ROLE.ADMIN.name)
        Crisis.objects.all().delete()
        self.crisis = CrisisFactory.create()
        self.events = EventFactory.create_batch(3, crisis=self.crisis)
        self.force_login(self.admin)

    def _run_capturing(self, query):
        with CaptureQueriesContext(connection) as ctx:
            response = self.query(query)
            self.assertResponseNoErrors(response)
        data = json.loads(response.content)["data"]
        counts = [q for q in ctx.captured_queries if 'COUNT(*) AS "c"' in q["sql"]]
        paged = [q for q in ctx.captured_queries if "ROW_NUMBER()" in q["sql"]]
        return data, paged, counts

    def _events_node(self, data, field="events"):
        node = next(r for r in data["crisisList"]["results"] if r["id"] == str(self.crisis.id))
        return node[field]

    def test_total_count_selected_fires_one_count_query(self) -> None:
        data, paged, counts = self._run_capturing(
            """
            query WithTotalCount {
              crisisList(ordering: "id") {
                results { id events(pageSize: 2) { totalCount results { id } } }
              }
            }
            """
        )
        self.assertEqual(len(counts), 1, [q["sql"] for q in counts])
        self.assertEqual(len(paged), 1, [q["sql"] for q in paged])
        self.assertEqual(self._events_node(data)["totalCount"], 3)

    def test_total_count_absent_fires_no_count_query(self) -> None:
        data, paged, counts = self._run_capturing(
            """
            query WithoutTotalCount {
              crisisList(ordering: "id") {
                results { id events(pageSize: 2) { results { id } } }
              }
            }
            """
        )
        self.assertEqual(counts, [], [q["sql"] for q in counts])
        # The page itself is still loaded, so the saving is the count query alone.
        self.assertEqual(len(paged), 1, [q["sql"] for q in paged])
        self.assertEqual(len(self._events_node(data)["results"]), 2)

    def test_total_count_through_alias(self) -> None:
        data, _, counts = self._run_capturing(
            """
            query AliasedTotalCount {
              crisisList(ordering: "id") {
                results { id events(pageSize: 2) { total: totalCount results { id } } }
              }
            }
            """
        )
        self.assertEqual(len(counts), 1, [q["sql"] for q in counts])
        self.assertEqual(self._events_node(data)["total"], 3)

    def test_response_key_totalcount_aliasing_another_field_fires_no_count_query(self) -> None:
        # The document names `page`, not `totalCount`: the response key is irrelevant, the
        # selected field decides.
        data, _, counts = self._run_capturing(
            """
            query MisleadingAlias {
              crisisList(ordering: "id") {
                results { id events(pageSize: 2) { totalCount: page results { id } } }
              }
            }
            """
        )
        self.assertEqual(counts, [], [q["sql"] for q in counts])
        self.assertEqual(self._events_node(data)["totalCount"], 1)

    def test_total_count_through_fragment(self) -> None:
        data, _, counts = self._run_capturing(
            """
            query FragmentTotalCount {
              crisisList(ordering: "id") {
                results { id events(pageSize: 2) { ...Totals results { id } } }
              }
            }
            fragment Totals on EventListType { totalCount }
            """
        )
        self.assertEqual(len(counts), 1, [q["sql"] for q in counts])
        self.assertEqual(self._events_node(data)["totalCount"], 3)

    def test_total_count_through_nested_fragment(self) -> None:
        data, _, counts = self._run_capturing(
            """
            query NestedFragmentTotalCount {
              crisisList(ordering: "id") {
                results { id events(pageSize: 2) { ...Outer results { id } } }
              }
            }
            fragment Outer on EventListType { ...Inner }
            fragment Inner on EventListType { renamed: totalCount }
            """
        )
        self.assertEqual(len(counts), 1, [q["sql"] for q in counts])
        self.assertEqual(self._events_node(data)["renamed"], 3)

    def test_total_count_through_inline_fragment(self) -> None:
        data, _, counts = self._run_capturing(
            """
            query InlineFragmentTotalCount {
              crisisList(ordering: "id") {
                results { id events(pageSize: 2) { ... on EventListType { totalCount } results { id } } }
              }
            }
            """
        )
        self.assertEqual(len(counts), 1, [q["sql"] for q in counts])
        self.assertEqual(self._events_node(data)["totalCount"], 3)

    def test_selecting_and_not_selecting_agree_on_the_page(self) -> None:
        # Equivalence: gating the count changes nothing else about the payload.
        page_query = """
            query Page {
              crisisList(ordering: "id") {
                results { id events(pageSize: 2) { %s results { id } page pageSize } }
              }
            }
        """
        with_count, _, _ = self._run_capturing(page_query % "totalCount")
        without_count, _, _ = self._run_capturing(page_query % "")
        counted = self._events_node(with_count)
        uncounted = self._events_node(without_count)
        self.assertEqual(counted["results"], uncounted["results"])
        self.assertEqual((counted["page"], counted["pageSize"]), (uncounted["page"], uncounted["pageSize"]))


class TestUnpaginatedNestedListTotalCount(HelixGraphQLTestCase):
    """A nested list with no page params loads every child row of each parent, so its
    total is the size of the loaded group and costs no query of its own."""

    def setUp(self) -> None:
        self.admin = create_user_with_role(USER_ROLE.ADMIN.name)
        self.entry = EntryFactory.create()
        self.event = EventFactory.create()
        Figure.objects.all().delete()
        self.figure = FigureFactory.create(entry=self.entry, event=self.event)
        self.sources = OrganizationFactory.create_batch(3)
        self.figure.sources.add(*self.sources)
        # A source organization in two countries: a filter joining that M2M would fan the
        # organization out into two rows, and the total must not follow.
        self.countries = CountryFactory.create_batch(2)
        self.sources[0].countries.add(*self.countries)
        self.childless = FigureFactory.create(entry=self.entry, event=self.event)
        self.force_login(self.admin)

    def _run_capturing(self, query, variables=None):
        with CaptureQueriesContext(connection) as ctx:
            response = self.query(query, variables=variables)
            self.assertResponseNoErrors(response)
        data = json.loads(response.content)["data"]
        counts = [q for q in ctx.captured_queries if 'COUNT(*) AS "c"' in q["sql"]]
        return data, counts

    def _sources_node(self, data):
        return next(r for r in data["figureList"]["results"] if r["id"] == str(self.figure.id))["sources"]

    def test_total_count_needs_no_count_query(self) -> None:
        data, counts = self._run_capturing(
            """
            query FigureSources {
              figureList(ordering: "id") {
                results { id sources { totalCount results { id } } }
              }
            }
            """
        )
        node = self._sources_node(data)
        self.assertEqual(node["totalCount"], 3)
        self.assertEqual({s["id"] for s in node["results"]}, {str(s.id) for s in self.sources})
        childless = next(r for r in data["figureList"]["results"] if r["id"] == str(self.childless.id))
        self.assertEqual(childless["sources"]["totalCount"], 0)
        self.assertEqual(childless["sources"]["results"], [])
        self.assertEqual(counts, [], [q["sql"] for q in counts])

    def test_total_count_matches_the_relation_count_under_a_filter(self) -> None:
        # The filter selects the two-country organization; the total counts organizations,
        # not the rows a joined M2M would have produced.
        data, counts = self._run_capturing(
            """
            query FilteredFigureSources($countries: [ID!]) {
              figureList(ordering: "id") {
                results { id sources(filters: { countries: $countries }) { totalCount results { id } } }
              }
            }
            """,
            variables={"countries": [str(c.id) for c in self.countries]},
        )
        node = self._sources_node(data)
        self.assertEqual(node["totalCount"], 1)
        self.assertEqual([s["id"] for s in node["results"]], [str(self.sources[0].id)])
        self.assertEqual(
            node["totalCount"],
            self.figure.sources.filter(countries__in=self.countries).distinct().count(),
        )
        self.assertEqual(counts, [], [q["sql"] for q in counts])
