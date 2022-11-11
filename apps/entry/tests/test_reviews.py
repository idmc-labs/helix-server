import json
from apps.users.enums import USER_ROLE
from apps.entry.models import Figure
from apps.event.models import Event
from utils.factories import (
    EventFactory,
    FigureFactory,
    UnifiedReviewCommentFactory,
)
from utils.tests import HelixGraphQLTestCase, create_user_with_role


class TestEventReviewGraphQLTestCase(HelixGraphQLTestCase):
    def setUp(self) -> None:
        self.event = EventFactory.create()
        self.regional_coordinator = create_user_with_role(USER_ROLE.REGIONAL_COORDINATOR.name)
        self.monitoring_expert = create_user_with_role(USER_ROLE.MONITORING_EXPERT.name)
        self.admin = create_user_with_role(USER_ROLE.ADMIN.name)
        self.guest = create_user_with_role(USER_ROLE.GUEST.name)
        self.approve_figure = '''
        mutation approveFigure($id: ID!) {
            approveFigure(id: $id) {
               errors
                ok
                result {
                  id
                  reviewStatus
                }
            }
        }
        '''
        self.unapprove_figure = '''
        mutation unapproveFigure($id: ID!) {
            unapproveFigure(id: $id) {
               errors
                ok
                result {
                  id
                  reviewStatus
                }
            }
        }
        '''
        self.re_request_review_figure = '''
        mutation reRequestReviewFigure($id: ID!) {
            reRequestReviewFigure(id: $id) {
               errors
                ok
                result {
                  id
                  reviewStatus
                }
            }
        }
        '''
        self.update_event = '''mutation UpdateEvent($input: EventUpdateInputType!) {
            updateEvent(data: $input) {
                errors
                result {
                    id
                    reviewStatus
                    includeTriangulationInQa
                }
                ok
                }
            }'''
        self.event = EventFactory.create(assigner=self.regional_coordinator, assignee=self.monitoring_expert)
        self.figure = FigureFactory.create(event=self.event)

    def test_all_users_can_approve_figure_except_guest(self) -> None:
        users = [self.admin, self.monitoring_expert, self.regional_coordinator]
        for user in users:
            self.force_login(user)
            input = {'id': self.figure.id}
            response = self.query(
                self.approve_figure,
                variables=input,
            )
            content = json.loads(response.content)
            self.assertResponseNoErrors(response)
            self.assertTrue(content['data']['approveFigure']['ok'], content)
            self.assertIsNone(content['data']['approveFigure']['errors'], content)

            self.assertEqual(content['data']['approveFigure']['result']['id'], str(self.figure.id))
            self.assertEqual(
                content['data']['approveFigure']['result']['reviewStatus'],
                Figure.FigureReviewStatus.APPROVED.name
            )

    def test_all_users_can_unapprove_figure_except_guest(self) -> None:
        users = [self.admin, self.monitoring_expert, self.regional_coordinator]
        for user in users:
            self.force_login(user)
            input = {'id': self.figure.id}
            response = self.query(
                self.unapprove_figure,
                variables=input,
            )
            content = json.loads(response.content)
            self.assertResponseNoErrors(response)
            self.assertTrue(content['data']['unapproveFigure']['ok'], content)
            self.assertIsNone(content['data']['unapproveFigure']['errors'], content)

            self.assertEqual(content['data']['unapproveFigure']['result']['id'], str(self.figure.id))
            self.assertEqual(
                content['data']['unapproveFigure']['result']['reviewStatus'],
                Figure.FigureReviewStatus.REVIEW_NOT_STARTED.name
            )

    def test_all_users_can_re_request_review_figure_except_guest(self) -> None:
        users = [self.admin, self.monitoring_expert, self.regional_coordinator]
        for user in users:
            self.force_login(user)
            input = {'id': self.figure.id}
            response = self.query(
                self.re_request_review_figure,
                variables=input,
            )
            content = json.loads(response.content)
            self.assertResponseNoErrors(response)
            self.assertTrue(content['data']['reRequestReviewFigure']['ok'], content)
            self.assertIsNone(content['data']['reRequestReviewFigure']['errors'], content)

            self.assertEqual(content['data']['reRequestReviewFigure']['result']['id'], str(self.figure.id))
            self.assertEqual(
                content['data']['reRequestReviewFigure']['result']['reviewStatus'],
                Figure.FigureReviewStatus.REVIEW_RE_REQUESTED.name
            )

    def test_review_status_should_be_review_in_progress_if_figure_has_review_comments_during_unapprove(self) -> None:
        users = [self.admin, self.monitoring_expert, self.regional_coordinator]
        UnifiedReviewCommentFactory.create(figure=self.figure, event=self.event)
        for user in users:
            self.force_login(user)
            input = {'id': self.figure.id}
            response = self.query(
                self.unapprove_figure,
                variables=input,
            )
            content = json.loads(response.content)
            self.assertResponseNoErrors(response)
            self.assertTrue(content['data']['unapproveFigure']['ok'], content)
            self.assertIsNone(content['data']['unapproveFigure']['errors'], content)
            self.assertEqual(content['data']['unapproveFigure']['result']['id'], str(self.figure.id))
            self.assertEqual(
                content['data']['unapproveFigure']['result']['reviewStatus'],
                Figure.FigureReviewStatus.REVIEW_IN_PROGRESS.name
            )

    def test_event_status_should_be_changed_if_figure_status_updated(self) -> None:
        self.force_login(self.admin)

        event = EventFactory.create(include_triangulation_in_qa=True)
        f1, f2, f3 = FigureFactory.create_batch(3, event=event, role=Figure.ROLE.RECOMMENDED)
        f4 = FigureFactory.create(event=event, role=Figure.ROLE.TRIANGULATION)

        # Initially event type should be REVIEW_NOT_STARTED
        self.assertEqual(event.review_status, event.EventReviewStatus.REVIEW_NOT_STARTED)

        # If any figure one of many event figures is approved review status should be REVIEW_IN_PROGRESS
        response = self.query(
            self.approve_figure,
            variables={'id': f1.id}
        )
        self.assertResponseNoErrors(response)
        event.refresh_from_db()
        self.assertEqual(event.review_status, event.EventReviewStatus.REVIEW_IN_PROGRESS)

        # After all figures approved event should be also approved
        for figure in [f2, f3, f4]:
            response = self.query(
                self.approve_figure,
                variables={'id': figure.id}
            )
            self.assertResponseNoErrors(response)
        event.refresh_from_db()
        self.assertEqual(event.review_status, event.EventReviewStatus.APPROVED)

        # If review re-requested event status should be changes to REVIEW_IN_PROGRESS
        response = self.query(
            self.re_request_review_figure,
            variables={'id': f1.id}
        )
        self.assertResponseNoErrors(response)

        event.refresh_from_db()
        self.assertEqual(event.review_status, event.EventReviewStatus.REVIEW_IN_PROGRESS)

    def test_event_status_should_be_calculated_if_include_triangulation_in_qa_is_changed(self):
        event = EventFactory.create(include_triangulation_in_qa=False, review_status=Event.EventReviewStatus.APPROVED)
        FigureFactory.create(event=event, role=Figure.ROLE.TRIANGULATION)
        self.assertEqual(event.review_status, event.EventReviewStatus.APPROVED)

        self.force_login(self.regional_coordinator)
        response = self.query(
            self.update_event,
            input_data={'id': event.id, 'includeTriangulationInQa': True}
        )
        content = json.loads(response.content)
        self.assertResponseNoErrors(response)
        self.assertTrue(content['data']['updateEvent']['ok'], content)

        event.refresh_from_db()
        self.assertEqual(event.review_status, event.EventReviewStatus.REVIEW_NOT_STARTED)
