from apps.users.enums import USER_ROLE
from utils.factories import UnifiedReviewCommentFactory
from utils.tests import HelixGraphQLTestCase, create_user_with_role


class TestUpdateReviewComment(HelixGraphQLTestCase):
    def setUp(self) -> None:
        self.creator = create_user_with_role(USER_ROLE.MONITORING_EXPERT.name)
        self.instance = UnifiedReviewCommentFactory.create(created_by=self.creator)
        self.mutation = '''
        mutation($input: CommentUpdateInputType!){
          updateReviewComment(data: $input) {
            ok
            errors
            result {
              comment
            }
          }
        }
        '''
        self.input = {
            "id": self.instance.id,
            "comment": "updated comment comment",
        }

    def test_valid_review_comment_update(self) -> None:
        self.force_login(self.creator)
        response = self.query(
            self.mutation,
            input_data=self.input
        )

        content = response.json()

        self.assertResponseNoErrors(response)
        self.assertTrue(content['data']['updateReviewComment']['ok'], content)
        self.assertEqual(content['data']['updateReviewComment']['result']['comment'],
                         self.input['comment'])

    def test_invalid_review_comment_update_by_non_creator(self) -> None:
        different_user = create_user_with_role(USER_ROLE.MONITORING_EXPERT.name)
        self.force_login(different_user)
        response = self.query(
            self.mutation,
            input_data=self.input
        )

        content = response.json()
        self.assertEqual('nonFieldErrors',
                         content['data']['updateReviewComment']['errors'][0]['field'])
        self.assertIn('does not exist',
                      content['data']['updateReviewComment']['errors'][0]['messages'].lower())


class TestDeleteReviewComment(HelixGraphQLTestCase):
    def setUp(self) -> None:
        self.creator = create_user_with_role(USER_ROLE.MONITORING_EXPERT.name)
        self.instance = UnifiedReviewCommentFactory.create(created_by=self.creator)
        self.mutation = '''
        mutation DeleteReviewComment($id: ID!) {
          deleteReviewComment(id: $id) {
            ok
            errors
            result {
              id
              comment
            }
          }
        }
        '''
        self.variables = {
            "id": str(self.instance.id),
        }

    def test_valid_review_comment_delete(self) -> None:
        self.force_login(self.instance.created_by)
        response = self.query(
            self.mutation,
            variables=self.variables
        )

        content = response.json()

        self.assertResponseNoErrors(response)
        self.assertTrue(content['data']['deleteReviewComment']['ok'], content)
        self.assertEqual(content['data']['deleteReviewComment']['result']['id'],
                         self.variables['id'])

    def test_invalid_review_comment_delete_by_non_creator(self) -> None:
        reviewer = create_user_with_role(USER_ROLE.MONITORING_EXPERT.name)
        self.force_login(reviewer)
        response = self.query(
            self.mutation,
            variables=self.variables
        )

        content = response.json()
        self.assertIn('nonFieldErrors',
                      content['data']['deleteReviewComment']['errors'][0]['field'])
        self.assertIn('does not exist',
                      content['data']['deleteReviewComment']['errors'][0]['messages'].lower())
