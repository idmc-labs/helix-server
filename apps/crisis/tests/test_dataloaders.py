import json

from django.db import connection
from django.test.utils import CaptureQueriesContext

from apps.crisis.models import Crisis
from apps.users.enums import USER_ROLE
from utils.factories import (
    CrisisFactory,
    EntryFactory,
    EventFactory,
    FigureFactory,
    OrganizationFactory,
)
from utils.tests import HelixGraphQLTestCase, create_user_with_role


class TestGenericDataLoaders(HelixGraphQLTestCase):
    """Guards the generic ``utils.graphene.dataloaders`` OneToManyLoader / CountLoader that back
    every ``DjangoPaginatedListObjectField`` exposed under a list path.

    Covers the engine's code-path matrix:
      - OneToManyLoader python-group path  (unpaginated reverse-M2M: figure.sources)
      - OneToManyLoader window-CTE path    (paginated reverse-FK: crisis.events(pageSize:N))
      - CountLoader grouped-count path     (crisis.events.totalCount)
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
        # OneToManyLoader python-group path: figure.sources has no pageSize param, so the field
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
        # OneToManyLoader window-CTE path: crisis.events declares pageSize. Default ordering is
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
        # ...while CountLoader reports the full related total, independent of the page slice.
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
        # events) and capture again. Because OneToManyLoader / CountLoader batch every parent key
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
