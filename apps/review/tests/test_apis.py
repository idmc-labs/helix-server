from apps.users.enums import USER_ROLE
from apps.entry.models import Figure
from apps.review.models import UnifiedReviewComment
from utils.factories import UnifiedReviewCommentFactory, EventFactory, FigureFactory
from utils.tests import HelixGraphQLTestCase, create_user_with_role


class TestReviewComment(HelixGraphQLTestCase):
    def setUp(self) -> None:
        self.creator = create_user_with_role(USER_ROLE.MONITORING_EXPERT.name)
        self.instance = UnifiedReviewCommentFactory.create(created_by=self.creator)

        self.admin = create_user_with_role(USER_ROLE.ADMIN.name)
        self.regional_coordinator = create_user_with_role(USER_ROLE.REGIONAL_COORDINATOR.name)
        self.monitoring_expert = create_user_with_role(USER_ROLE.MONITORING_EXPERT.name)

        self.event = EventFactory.create(
            assigner=self.admin,
            assignee=self.regional_coordinator,
        )
        self.figure = FigureFactory.create(
            event=self.event,
            role=Figure.ROLE.RECOMMENDED
        )

        self.create_comment = '''
        mutation($input: UnifiedReviewCommentCreateInputType!){
          createReviewComment(data: $input) {
            ok
            errors
            result {
              comment
              figure {
                id
                reviewStatus
              }
            }
          }
        }
        '''

        self.update_comment = '''
        mutation($input: UnifiedReviewCommentUpdateInputType!){
          updateReviewComment(data: $input) {
            ok
            errors
            result {
              comment
              figure {
                id
                reviewStatus
              }
            }
          }
        }
        '''
        self.input = {
            "id": self.instance.id,
            "comment": "updated comment comment",
        }
        self.create_input = {
            "comment": "updated comment comment",
            "figure": self.figure.id,
            "event": self.event.id,
        }

    def test_valid_review_comment_update(self) -> None:
        self.force_login(self.creator)
        response = self.query(
            self.update_comment,
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
            self.update_comment,
            input_data=self.input
        )

        content = response.json()
        self.assertEqual('nonFieldErrors',
                         content['data']['updateReviewComment']['errors'][0]['field'])
        self.assertIn('does not exist',
                      content['data']['updateReviewComment']['errors'][0]['messages'].lower())

    def test_assignee_can_create_all_types_of_comments(self):
        self.force_login(self.regional_coordinator)
        for comment_type in [
            UnifiedReviewComment.REVIEW_COMMENT_TYPE.GREEN.name,
            UnifiedReviewComment.REVIEW_COMMENT_TYPE.RED.name,
            UnifiedReviewComment.REVIEW_COMMENT_TYPE.GREY.name,
        ]:
            self.create_input['commentType'] = comment_type
            response = self.query(
                self.create_comment,
                input_data=self.create_input
            )
            content = response.json()
            self.assertResponseNoErrors(response)
            self.assertTrue(content['data']['createReviewComment']['ok'], content)
            self.assertEqual(content['data']['createReviewComment']['result']['comment'],
                             self.input['comment'])

    def test_other_than_assignee_can_create_general_comment(self):
        for user in [
            self.admin,
            self.monitoring_expert,
        ]:
            self.force_login(user)
            self.create_input['commentType'] = UnifiedReviewComment.REVIEW_COMMENT_TYPE.GREY.name
            response = self.query(
                self.create_comment,
                input_data=self.create_input
            )
            content = response.json()
            self.assertResponseNoErrors(response)
            self.assertTrue(content['data']['createReviewComment']['ok'], content)
            self.assertEqual(content['data']['createReviewComment']['result']['comment'],
                             self.input['comment'])

    def test_other_than_assignee_can_not_create_approval_comments(self):
        for user in [
            self.admin,
            self.monitoring_expert,
        ]:
            self.force_login(user)
            for comment_type in [
                UnifiedReviewComment.REVIEW_COMMENT_TYPE.GREEN.name,
                UnifiedReviewComment.REVIEW_COMMENT_TYPE.RED.name,
            ]:
                self.create_input['commentType'] = comment_type
                response = self.query(
                    self.create_comment,
                    input_data=self.create_input
                )
                content = response.json()
                self.assertResponseNoErrors(response)
                self.assertFalse(content['data']['createReviewComment']['ok'])

    def test_new_comment_should_change_review_not_started_to_in_progress(self):
        self.force_login(self.regional_coordinator)

        figure = FigureFactory.create(
            event=self.event,
            role=Figure.ROLE.RECOMMENDED,
            review_status=Figure.FIGURE_REVIEW_STATUS.REVIEW_NOT_STARTED,
        )

        self.create_input['commentType'] = UnifiedReviewComment.REVIEW_COMMENT_TYPE.GREEN.name
        self.create_input['figure'] = figure.id
        response = self.query(
            self.create_comment,
            input_data=self.create_input
        )
        content = response.json()
        print(content)
        self.assertEqual(
            content['data']['createReviewComment']['result']['figure']['reviewStatus'],
            Figure.FIGURE_REVIEW_STATUS.REVIEW_IN_PROGRESS.name,
        )

    def test_comment_from_assignee_should_change_review_requested_to_in_progress(self):
        self.force_login(self.regional_coordinator)

        figure = FigureFactory.create(
            event=self.event,
            role=Figure.ROLE.RECOMMENDED,
            review_status=Figure.FIGURE_REVIEW_STATUS.REVIEW_RE_REQUESTED,
        )

        self.create_input['commentType'] = UnifiedReviewComment.REVIEW_COMMENT_TYPE.RED.name
        self.create_input['figure'] = figure.id
        response = self.query(
            self.create_comment,
            input_data=self.create_input
        )
        content = response.json()
        print(content)
        self.assertEqual(
            content['data']['createReviewComment']['result']['figure']['reviewStatus'],
            Figure.FIGURE_REVIEW_STATUS.REVIEW_IN_PROGRESS.name,
        )

    def test_comment_from_non_assignee_should_not_change_review_requested_to_in_progress(self):
        self.force_login(self.monitoring_expert)

        figure = FigureFactory.create(
            event=self.event,
            role=Figure.ROLE.RECOMMENDED,
            review_status=Figure.FIGURE_REVIEW_STATUS.REVIEW_RE_REQUESTED,
        )

        self.create_input['commentType'] = UnifiedReviewComment.REVIEW_COMMENT_TYPE.GREY.name
        self.create_input['figure'] = figure.id
        response = self.query(
            self.create_comment,
            input_data=self.create_input
        )
        content = response.json()
        print(content)
        self.assertEqual(
            content['data']['createReviewComment']['result']['figure']['reviewStatus'],
            Figure.FIGURE_REVIEW_STATUS.REVIEW_RE_REQUESTED.name,
        )


class TestDeleteReviewComment(HelixGraphQLTestCase):
    def setUp(self) -> None:
        self.creator = create_user_with_role(USER_ROLE.MONITORING_EXPERT.name)
        self.instance = UnifiedReviewCommentFactory.create(created_by=self.creator)
        self.delete_comment = '''
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
            self.delete_comment,
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
            self.delete_comment,
            variables=self.variables
        )

        content = response.json()
        self.assertIn('nonFieldErrors',
                      content['data']['deleteReviewComment']['errors'][0]['field'])
        self.assertIn('does not exist',
                      content['data']['deleteReviewComment']['errors'][0]['messages'].lower())
