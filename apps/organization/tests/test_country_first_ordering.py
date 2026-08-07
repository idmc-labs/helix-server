import json

from apps.users.enums import USER_ROLE
from utils.factories import CountryFactory, EntryFactory, OrganizationFactory
from utils.tests import HelixGraphQLTestCase, create_user_with_role


class TestOrderCountryFirstSurvivesASort(HelixGraphQLTestCase):
    """`orderCountryFirst` buckets the organizations of the given countries to the front.

    It is a filter that orders, so it reaches pagination as a queryset that already carries an
    ordering. Two things follow: the client's own `ordering` must not replace the bucket, and
    the bucket -- two values across the whole table -- must not be the last word on row order,
    or every row in a bucket pages in plan-dependent order.
    """

    def setUp(self) -> None:
        self.user = create_user_with_role(USER_ROLE.ADMIN.name)
        self.force_login(self.user)
        self.country = CountryFactory.create()
        # The bucketed organization sorts in the MIDDLE by name, so neither an ascending nor
        # a descending sort could put it first on its own -- only the bucket can.
        self.in_country = OrganizationFactory.create(name="mike-org")
        self.in_country.countries.add(self.country)
        self.others = [OrganizationFactory.create(name=name) for name in ("alpha-org", "zulu-org")]

    def _query(self, ordering=None):
        response = self.query(
            """
            query MyQuery($filters: OrganizationFilterDataInputType, $ordering: String) {
              organizationList(filters: $filters, ordering: $ordering) { results { id name } }
            }
            """,
            variables={
                "filters": {"orderCountryFirst": [str(self.country.id)]},
                "ordering": ordering,
            },
        )
        content = json.loads(response.content)
        self.assertResponseNoErrors(response)
        return [o["name"] for o in content["data"]["organizationList"]["results"]]

    def test_the_bucket_leads_when_nothing_else_is_requested(self):
        self.assertEqual(self._query()[0], "mike-org")

    def test_the_bucket_still_leads_when_the_caller_also_sorts(self):
        names = self._query(ordering="name")
        self.assertEqual(names[0], "mike-org", "orderCountryFirst was dropped by the client's sort")
        self.assertEqual(names[1:], ["alpha-org", "zulu-org"], names)

    def test_the_bucket_still_leads_under_a_descending_sort(self):
        names = self._query(ordering="-name")
        self.assertEqual(names[0], "mike-org", names)
        self.assertEqual(names[1:], ["zulu-org", "alpha-org"], names)

    def test_rows_inside_a_bucket_are_pageable(self):
        """The bucket alone leaves every row in it tied, which is not a pageable order.

        Two identical executions of one plan agree even without a tiebreaker, so comparing
        them proves nothing. Walk the list one row per page instead: without the pk
        completion the pages overlap or skip.
        """
        paged = []
        for page in (1, 2, 3):
            response = self.query(
                """
                query MyQuery($filters: OrganizationFilterDataInputType, $page: Int!) {
                  organizationList(filters: $filters, page: $page, pageSize: 1) {
                    results { id name }
                  }
                }
                """,
                variables={"filters": {"orderCountryFirst": [str(self.country.id)]}, "page": page},
            )
            content = json.loads(response.content)
            self.assertResponseNoErrors(response)
            paged += [organization["name"] for organization in content["data"]["organizationList"]["results"]]
        self.assertEqual(paged[0], "mike-org", paged)
        self.assertEqual(sorted(paged), ["alpha-org", "mike-org", "zulu-org"], f"pages overlap or skip: {paged}")

    def test_the_single_object_route_keeps_the_bucket_too(self):
        """`entry(id:) { publishers(...) }` is served by OrderingOnlyArgumentPagination.

        A single-object parent does not satisfy `path_has_list`, so this field reaches
        `order_by()` by a different route than the same field inside `entryList`. Both must
        honour the bucket, or identical arguments give two different orders.
        """
        entry = EntryFactory.create(created_by=self.user)
        entry.publishers.set([self.in_country, *self.others])

        response = self.query(
            """
            query MyQuery($id: ID!, $filters: OrganizationFilterDataInputType) {
              entry(id: $id) {
                id
                publishers(filters: $filters, ordering: "name") { results { id name } }
              }
            }
            """,
            variables={"id": str(entry.id), "filters": {"orderCountryFirst": [str(self.country.id)]}},
        )
        content = json.loads(response.content)
        self.assertResponseNoErrors(response)
        names = [organization["name"] for organization in content["data"]["entry"]["publishers"]["results"]]
        self.assertEqual(names, ["mike-org", "alpha-org", "zulu-org"], names)
