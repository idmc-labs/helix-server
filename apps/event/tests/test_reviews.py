import json
from apps.users.enums import USER_ROLE
from utils.factories import EventFactory, FigureFactory
from apps.event.models import Event
from apps.entry.models import Figure
from utils.tests import HelixGraphQLTestCase, create_user_with_role


class TestEventReviewGraphQLTestCase(HelixGraphQLTestCase):
    def setUp(self) -> None:
        self.event = EventFactory.create()
        self.regional_coordinator = create_user_with_role(USER_ROLE.REGIONAL_COORDINATOR.name)
        self.monitoring_expert = create_user_with_role(USER_ROLE.MONITORING_EXPERT.name)
        self.admin = create_user_with_role(USER_ROLE.ADMIN.name)
        self.guest = create_user_with_role(USER_ROLE.GUEST.name)
        self.set_assignee_to_event_mutation = '''
        mutation setAssigneeToEvent($event_id: ID!, $user_id: ID!) {
            setAssigneeToEvent(eventId: $event_id, userId: $user_id) {
                errors
                result {
                  id
                  name
                  assigner{
                    id
                  }
                  assignee {
                    id
                  }
               }
              ok
              errors
            }
        }
        '''
        self.set_self_assignee_to_event_mutation = '''
        mutation setSelfAssigneeToEvent($event_id: ID!) {
            setSelfAssigneeToEvent(eventId: $event_id) {
                errors
                result {
                  id
                  name
                  assigner{
                    id
                  }
                  assignee {
                    id
                  }
               }
              ok
              errors
            }
        }
        '''
        self.clear_assignee_from_event_mutation = '''
        mutation clearAssigneeFromEvent($event_id: ID!) {
            clearAssigneeFromEvent(eventId: $event_id) {
                errors
                result {
                  id
                  name
                  assigner{
                    id
                  }
                  assignee {
                    id
                  }
               }
              ok
              errors
            }
        }
        '''
        self.clear_self_assignee_from_event_mutation = '''
        mutation clearSelfAssigneeFromEvent($event_id: ID!) {
            clearSelfAssigneeFromEvent(eventId: $event_id) {
                errors
                result {
                  id
                  name
                  assigner{
                    id
                  }
                  assignee {
                    id
                  }
               }
              ok
              errors
            }
        }
        '''
        self.sign_off_event = '''
        mutation signOffEvent($event_id: ID!) {
            signOffEvent(eventId: $event_id) {
                errors
                result {
                  id
                  reviewStatus
               }
              ok
              errors
            }
        }
        '''

    def test_user_can_set_assignee_on_an_event(self) -> None:
        # Test admin, regional_coordinator can be assign assignees
        assignee_assigners = (
            (self.regional_coordinator, self.regional_coordinator),
            (self.regional_coordinator, self.monitoring_expert),
            (self.regional_coordinator, self.admin),
            (self.admin, self.regional_coordinator),
            (self.admin, self.monitoring_expert),
            (self.admin, self.admin),
        )
        for assigner, assignee in assignee_assigners:
            self.force_login(assigner)
            input = {'event_id': self.event.id, 'user_id': assignee.id}
            response = self.query(
                self.set_assignee_to_event_mutation,
                variables=input,
            )
            content = json.loads(response.content)
            self.assertResponseNoErrors(response)
            self.assertTrue(content['data']['setAssigneeToEvent']['ok'], content)
            self.assertIsNone(content['data']['setAssigneeToEvent']['errors'], content)

            self.assertEqual(content['data']['setAssigneeToEvent']['result']['assignee']['id'], str(assignee.id))
            self.assertEqual(content['data']['setAssigneeToEvent']['result']['assigner']['id'], str(assigner.id))
        # Test guest should not be assignee
        guest_assignee_assigners = (
            (self.regional_coordinator, self.guest),
            (self.regional_coordinator, self.guest),
            (self.regional_coordinator, self.guest),
        )
        for assigner, assignee in guest_assignee_assigners:
            self.force_login(assigner)
            input = {'event_id': self.event.id, 'user_id': assignee.id}
            response = self.query(
                self.set_assignee_to_event_mutation,
                variables=input,
            )
            content = json.loads(response.content)
            self.assertIsNotNone(content['data']['setAssigneeToEvent']['errors'])

        # Test monitoring expert should not assign assignee
        assignee_assigners = (
            (self.monitoring_expert, self.admin),
            (self.monitoring_expert, self.regional_coordinator),
            (self.monitoring_expert, self.monitoring_expert),
        )
        for assigner, assignee in assignee_assigners:
            self.force_login(assigner)
            input = {'event_id': self.event.id, 'user_id': assignee.id}
            response = self.query(
                self.set_assignee_to_event_mutation,
                variables=input,
            )
            content = json.loads(response.content)
            self.assertIsNotNone(content['errors'])

        # Test guest should not assign assignee
        assignee_assigners = (
            (self.guest, self.admin),
            (self.guest, self.regional_coordinator),
            (self.guest, self.monitoring_expert),
        )
        for assigner, assignee in assignee_assigners:
            self.force_login(assigner)
            input = {'event_id': self.event.id, 'user_id': assignee.id}
            response = self.query(
                self.set_assignee_to_event_mutation,
                variables=input,
            )
            content = json.loads(response.content)
            self.assertIsNotNone(content['errors'])

    def test_self_event_assignment(self) -> None:

        # Admin, regional coordinator can assign self in an event
        users = [self.regional_coordinator, self.admin, self.monitoring_expert]
        for user in users:
            event = EventFactory.create(assigner=self.regional_coordinator, assignee=self.monitoring_expert)
            self.force_login(user)
            input = {'event_id': event.id}
            response = self.query(
                self.set_self_assignee_to_event_mutation,
                variables=input,
            )
            content = json.loads(response.content)
            self.assertResponseNoErrors(response)
            self.assertTrue(content['data']['setSelfAssigneeToEvent']['ok'], content)
            self.assertEqual(content['data']['setSelfAssigneeToEvent']['result']['assigner']['id'], str(user.id))
            self.assertEqual(content['data']['setSelfAssigneeToEvent']['result']['assignee']['id'], str(user.id))

    def test_user_can_clear_assignee_on_an_event(self) -> None:

        # Test assigner or assignee or admin can clear assignee
        users = [self.regional_coordinator, self.admin]
        event = EventFactory.create(assigner=self.regional_coordinator, assignee=self.monitoring_expert)
        for user in users:
            self.force_login(user)
            input = {'event_id': event.id}
            response = self.query(
                self.clear_assignee_from_event_mutation,
                variables=input,
            )
            content = json.loads(response.content)
            self.assertResponseNoErrors(response)
            self.assertTrue(content['data']['clearAssigneeFromEvent']['ok'], content)
            self.assertIsNone(content['data']['clearAssigneeFromEvent']['errors'], content)
            self.assertIsNone(content['data']['clearAssigneeFromEvent']['result']['assigner'], None)
            self.assertIsNone(content['data']['clearAssigneeFromEvent']['result']['assignee'], None)

        # Test amdin and regional coordinator can clear other assignee from event
        admin_1 = create_user_with_role(USER_ROLE.ADMIN.name)
        regional_coordinator_1 = create_user_with_role(USER_ROLE.REGIONAL_COORDINATOR.name)
        for user in [admin_1, regional_coordinator_1]:
            # Set assignee and assigneer
            event.assigner = self.admin
            event.assignee = self.regional_coordinator
            event.save()

            self.force_login(user)
            input = {'event_id': event.id}
            response = self.query(
                self.clear_assignee_from_event_mutation,
                variables=input,
            )
            content = json.loads(response.content)
            self.assertResponseNoErrors(response)
            self.assertIsNone(content['data']['clearAssigneeFromEvent']['errors'])
            self.assertTrue(content['data']['clearAssigneeFromEvent']['ok'], content)
            self.assertIsNone(content['data']['clearAssigneeFromEvent']['errors'], content)
            self.assertIsNone(content['data']['clearAssigneeFromEvent']['result']['assigner'], None)
            self.assertIsNone(content['data']['clearAssigneeFromEvent']['result']['assignee'], None)

        # Test monitoring expert should not clear other assignee from event
        monitoring_expert_1 = create_user_with_role(USER_ROLE.MONITORING_EXPERT.name)
        self.force_login(monitoring_expert_1)
        input = {'event_id': event.id}
        response = self.query(
            self.clear_assignee_from_event_mutation,
            variables=input,
        )
        content = json.loads(response.content)
        self.assertIsNotNone(content['errors'])

    def test_all_users_can_clear_self_assignee_from_event(self) -> None:
        users = [self.regional_coordinator, self.admin, self.monitoring_expert]
        for user in users:
            event = EventFactory.create(assigner=self.admin, assignee=user)
            self.force_login(user)
            input = {'event_id': event.id}
            response = self.query(
                self.clear_self_assignee_from_event_mutation,
                variables=input,
            )
            content = json.loads(response.content)
            self.assertResponseNoErrors(response)
            self.assertTrue(content['data']['clearSelfAssigneeFromEvent']['ok'], content)
            self.assertIsNone(content['data']['clearSelfAssigneeFromEvent']['errors'], content)
            self.assertIsNone(content['data']['clearSelfAssigneeFromEvent']['result']['assigner'], None)

    def test_sign_off_event(self) -> None:
        users = [self.regional_coordinator, self.admin]
        for user in users:
            event = EventFactory.create(
                assigner=self.regional_coordinator,
                assignee=self.monitoring_expert,
                review_status=Event.EVENT_REVIEW_STATUS.APPROVED,
            )
            self.force_login(user)
            input = {'event_id': event.id}
            response = self.query(
                self.sign_off_event,
                variables=input,
            )
            content = json.loads(response.content)
            self.assertResponseNoErrors(response)
            self.assertTrue(content['data']['signOffEvent']['ok'], content)
            self.assertIsNone(content['data']['signOffEvent']['errors'], content)


class TestEventRewviewCount(HelixGraphQLTestCase):
    def setUp(self) -> None:
        self.event = EventFactory.create()
        self.admin = create_user_with_role(USER_ROLE.ADMIN.name)
        self.f1, self.f2, self.f3 = FigureFactory.create_batch(
            3,
            event=self.event,
            role=Figure.ROLE.RECOMMENDED,
            review_status=Figure.FIGURE_REVIEW_STATUS.REVIEW_NOT_STARTED,
        )
        self.event_query = '''
        query MyQuery {
          eventList {
            results {
              reviewCount {
                progress
                reviewApprovedCount
                reviewInProgressCount
                reviewNotStartedCount
                reviewReRequestCount
                totalCount
              }
            }
          }
        }
        '''

    def test_progress(self) -> None:
        self.force_login(self.admin)
        response = self.query(
            self.event_query,
        )
        content = json.loads(response.content)
        self.assertResponseNoErrors(response)
        # Initially all counts should be zero
        event_data = content['data']['eventList']['results'][0]
        self.assertEqual(event_data['reviewCount']['progress'], 0)
        self.assertEqual(event_data['reviewCount']['reviewApprovedCount'], 0)
        self.assertEqual(event_data['reviewCount']['reviewInProgressCount'], 0)
        self.assertEqual(event_data['reviewCount']['reviewNotStartedCount'], 3)
        self.assertEqual(event_data['reviewCount']['reviewReRequestCount'], 0)

        # Update figure status and check review counts
        self.f1.review_status = Figure.FIGURE_REVIEW_STATUS.REVIEW_IN_PROGRESS
        self.f1.save()
        response = self.query(
            self.event_query,
        )
        content = json.loads(response.content)
        self.assertResponseNoErrors(response)
        event_data = content['data']['eventList']['results'][0]
        self.assertEqual(event_data['reviewCount']['progress'], 0)
        self.assertEqual(event_data['reviewCount']['reviewApprovedCount'], 0)
        self.assertEqual(event_data['reviewCount']['reviewInProgressCount'], 1)
        self.assertEqual(event_data['reviewCount']['reviewNotStartedCount'], 2)
        self.assertEqual(event_data['reviewCount']['reviewReRequestCount'], 0)

        # Make all figures approved and check review counts
        for figure in [self.f1, self.f2, self.f3]:
            figure.review_status = Figure.FIGURE_REVIEW_STATUS.APPROVED
            figure.save()

        response = self.query(
            self.event_query,
        )
        content = json.loads(response.content)
        self.assertResponseNoErrors(response)
        event_data = content['data']['eventList']['results'][0]
        self.assertEqual(event_data['reviewCount']['progress'], 1.0)
        self.assertEqual(event_data['reviewCount']['reviewApprovedCount'], 3)
        self.assertEqual(event_data['reviewCount']['reviewInProgressCount'], 0)
        self.assertEqual(event_data['reviewCount']['reviewNotStartedCount'], 0)
        self.assertEqual(event_data['reviewCount']['reviewReRequestCount'], 0)
