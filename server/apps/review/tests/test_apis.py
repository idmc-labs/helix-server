from apps.users.enums import USER_ROLE
from utils.factories import ReviewCommentFactory
from utils.permissions import PERMISSION_DENIED_MESSAGE
from utils.tests import HelixGraphQLTestCase, create_user_with_role


class TestUpdateReviewComment(HelixGraphQLTestCase):
    def setUp(self) -> None:
        self.creator = create_user_with_role(USER_ROLE.MONITORING_EXPERT_REVIEWER.name)
        self.instance = ReviewCommentFactory.create(created_by=self.creator)
        self.mutation = '''
        mutation($input: CommentUpdateInputType!){
          updateComment(data: $input) {
            ok
            errors
            result {
              body
            }
          }
        }
        '''
        self.input = {
            "id": self.instance.id,
            "body": "updated body comment",
        }

    def test_valid_review_comment_update(self) -> None:
        self.force_login(self.creator)
        response = self.query(
            self.mutation,
            input_data=self.input
        )

        content = response.json()

        self.assertResponseNoErrors(response)
        self.assertTrue(content['data']['updateComment']['ok'], content)
        self.assertEqual(content['data']['updateComment']['result']['body'],
                         self.input['body'])

    def test_invalid_review_comment_update_by_non_creator(self) -> None:
        different_user = create_user_with_role(USER_ROLE.MONITORING_EXPERT_REVIEWER.name)
        self.force_login(different_user)
        response = self.query(
            self.mutation,
            input_data=self.input
        )

        content = response.json()
        self.assertEqual('nonFieldErrors',
                         content['data']['updateComment']['errors'][0]['field'])
        self.assertIn('does not exist',
                      content['data']['updateComment']['errors'][0]['messages'].lower())


class TestDeleteReviewComment(HelixGraphQLTestCase):
    def setUp(self) -> None:
        self.creator = create_user_with_role(USER_ROLE.MONITORING_EXPERT_REVIEWER.name)
        self.instance = ReviewCommentFactory.create(created_by=self.creator)
        self.mutation = '''
        mutation DeleteReviewComment($id: ID!) {
          deleteReviewComment(id: $id) {
            ok
            errors
            result {
              id
              body
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
        reviewer = create_user_with_role(USER_ROLE.MONITORING_EXPERT_REVIEWER.name)
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
