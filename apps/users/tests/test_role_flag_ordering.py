"""`users(ordering: "isAdmin")` and its two siblings must sort, not 400.

The role booleans are computed per user from their portfolios onto a nested type
(`portfoliosMetadata`), so there is no column to ORDER BY: `UserFilter` annotates each one as
an `Exists` over `Portfolio`, but only when the list is ordered by it, and the allowlist has
to name it as well. Those are TWO separate lists that must agree
(`UserFilter.ROLE_FLAG_ANNOTATIONS` and `User.ORDERING_ALLOWLIST`); delete either
side and the list regresses to a hard `Invalid ordering field`.
"""

import json

from apps.users.enums import USER_ROLE
from apps.users.filters import UserFilter
from apps.users.models import Portfolio, User
from utils.graphene.ordering import get_ordering_allowlist
from utils.tests import HelixGraphQLTestCase, create_user_with_role

USER_LIST_QUERY = """
    query MyQuery($ordering: String) {
      users(ordering: $ordering, pageSize: 50) {
        totalCount
        results {
          id
          portfoliosMetadata { isAdmin isDirectorsOffice isReportingTeam }
        }
      }
    }
"""

# The GraphQL token the client sends -> the snake_case annotation it is normalised to.
FLAGS = [
    ("isAdmin", "is_admin"),
    ("isDirectorsOffice", "is_directors_office"),
    ("isReportingTeam", "is_reporting_team"),
]


class TestRoleFlagOrdering(HelixGraphQLTestCase):
    @classmethod
    def setUpTestData(cls):
        # Two holders per role so the flagged block has an internal order to get wrong, and
        # guests so the unflagged block is not empty either.
        cls.users = [
            create_user_with_role(role)
            for role in (
                USER_ROLE.ADMIN.name,
                USER_ROLE.GUEST.name,
                USER_ROLE.DIRECTORS_OFFICE.name,
                USER_ROLE.REPORTING_TEAM.name,
                USER_ROLE.ADMIN.name,
                USER_ROLE.GUEST.name,
                USER_ROLE.DIRECTORS_OFFICE.name,
                USER_ROLE.REPORTING_TEAM.name,
            )
        ]
        cls.requester = create_user_with_role(USER_ROLE.ADMIN.name)

    def setUp(self) -> None:
        super().setUp()
        self.force_login(self.requester)

    def _holders(self, role):
        return set(Portfolio.objects.filter(role=role.value).values_list("user_id", flat=True))

    def _run(self, ordering):
        response = self.query(USER_LIST_QUERY, variables={"ordering": ordering})
        self.assertResponseNoErrors(response)
        return json.loads(response.content)["data"]["users"]

    def test_the_two_lists_that_have_to_agree_do_agree(self):
        # The annotation and the allowlist are maintained separately; either one alone is
        # useless. Pinned so deleting one side is a test failure, not a 400 in production.
        self.assertEqual(
            set(UserFilter.ROLE_FLAG_ANNOTATIONS) - get_ordering_allowlist(User),
            set(),
        )
        self.assertEqual(set(UserFilter.ROLE_FLAG_ANNOTATIONS), {"is_admin", "is_directors_office", "is_reporting_team"})

    def test_each_role_flag_orders_the_list_in_agreement_with_the_role_data(self):
        everyone = list(self.users) + [self.requester]
        for token, annotation in FLAGS:
            holders = self._holders(UserFilter.ROLE_FLAG_ANNOTATIONS[annotation])
            self.assertTrue(holders, "fixture stopped producing %s holders" % annotation)
            without = sorted(user.id for user in everyone if user.id not in holders)
            with_flag = sorted(user.id for user in everyone if user.id in holders)
            self.assertTrue(without, "fixture stopped producing non-%s users" % annotation)

            # nulls_last_order_queryset appends a pk tiebreaker that follows the primary key's
            # direction, so within each block the order is fully determined: oldest-first when
            # the flag is sorted ascending, newest-first when it is sorted descending.
            desc_without = list(reversed(without))
            desc_with_flag = list(reversed(with_flag))
            for ordering, expected in (
                (token, [str(pk) for pk in without + with_flag]),
                ("-" + token, [str(pk) for pk in desc_with_flag + desc_without]),
            ):
                with self.subTest(ordering=ordering):
                    payload = self._run(ordering)
                    self.assertEqual(payload["totalCount"], len(everyone), payload)
                    self.assertEqual([row["id"] for row in payload["results"]], expected, payload)

    def test_the_returned_flag_values_match_the_returned_order(self):
        # The order must agree with what portfoliosMetadata shows the client -- an annotation
        # that sorted on some other predicate would still return a sorted-looking id list.
        for token, _ in FLAGS:
            with self.subTest(ordering=token):
                flags = [row["portfoliosMetadata"][token] for row in self._run(token)["results"]]
                self.assertEqual(flags, sorted(flags), flags)
                self.assertIn(True, flags)
                self.assertIn(False, flags)
