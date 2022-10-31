import json
from apps.users.enums import USER_ROLE
from utils.factories import EventFactory
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

    def test_user_can_clear_assignee_on_an_event(self) -> None:

        # Test assigner or assignee or admin can clear assignee
        users = [self.regional_coordinator, self.monitoring_expert, self.admin]
        for user in users:
            event = EventFactory.create(assigner=self.regional_coordinator, assignee=self.monitoring_expert)
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

        # Test other users should not allowed to clear assignee
        regional_coordinator_1 = create_user_with_role(USER_ROLE.REGIONAL_COORDINATOR.name)
        monitoring_expert_1 = create_user_with_role(USER_ROLE.MONITORING_EXPERT.name)

        users = [self.guest, regional_coordinator_1, monitoring_expert_1]
        for user in users:
            self.force_login(user)
            input = {'event_id': event.id}
            response = self.query(
                self.clear_assignee_from_event_mutation,
                variables=input,
            )
            content = json.loads(response.content)
            self.assertResponseNoErrors(response)
            self.assertIsNotNone(content['data']['clearAssigneeFromEvent']['errors'])
