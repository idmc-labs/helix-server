import json
from uuid import uuid4
from apps.users.enums import USER_ROLE
from utils.factories import (
    EventFactory,
    EntryFactory,
    FigureFactory,
    CountryFactory,
    MonitoringSubRegionFactory,
    NotificationFactory,
)
from apps.notification.models import Notification
from utils.tests import HelixGraphQLTestCase, create_user_with_role
from apps.entry.models import Figure, OSMName
from apps.event.models import Event
from apps.crisis.models import Crisis
from apps.review.models import UnifiedReviewComment


class TestEventReviewGraphQLTestCase(HelixGraphQLTestCase):
    def setUp(self) -> None:
        self.country = CountryFactory.create()
        self.monitoring_sub_region = MonitoringSubRegionFactory.create()
        self.regional_coordinator = create_user_with_role(
            USER_ROLE.REGIONAL_COORDINATOR.name,
            country=self.country.id,
            monitoring_sub_region=self.monitoring_sub_region.id,
        )
        self.monitoring_expert = create_user_with_role(
            USER_ROLE.MONITORING_EXPERT.name,
            country=self.country.id,
            monitoring_sub_region=self.monitoring_sub_region.id,
        )
        self.admin = create_user_with_role(
            USER_ROLE.ADMIN.name,
            country=self.country.id,
            monitoring_sub_region=self.monitoring_sub_region.id,
        )

        self.delete_figure = '''
            mutation DeleteFigure($id: ID!) {
                deleteFigure(id: $id) {
                    ok
                    errors
                    result {
                        id
                    }
                }
            }
        '''
        self.create_update_figure = """
        mutation MyMutation($input: EntryUpdateInputType!) {
          updateEntry(data: $input) {
            ok
            errors
            result {
              id
              figures {
                id
              }
            }
          }
        }
        """
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
        self.notification_query = '''
        query MyQuery($recipient: ID!) {
          notifications(recipient: $recipient, ordering: "-id") {
            results {
                  id
                  createdAt
                  isRead
                  type
                  typeDisplay
                  entry {
                      id
                  }
           }
          }
        }
        '''
        self.create_review_comment = '''
        mutation($input: UnifiedReviewCommentCreateInputType!){
          createReviewComment(data: $input) {
            ok
            errors
            result {
              comment
            }
          }
        }
        '''
        self.update_event = '''
          mutation UpdateEvent($input: EventUpdateInputType!) {
            updateEvent(data: $input) {
              errors
              result {
                  id
                  name
              }
              ok
            }
          }
          '''
        self.toggle_notificaiton_read = '''
          mutation ToggleNotificationRead($id: ID!) {
            toggleNotificationRead(id: $id) {
              ok
              errors
              result {
                  id
                  isRead
              }
            }
          }

        '''
        source = dict(
            uuid=str(uuid4()),
            rank=101,
            country=str(self.country.name),
            countryCode=self.country.iso2,
            osmId='ted',
            osmType='okay',
            displayName='okay',
            lat=68.88,
            lon=46.66,
            name='name',
            accuracy=OSMName.OSM_ACCURACY.ADM0.name,
            identifier=OSMName.IDENTIFIER.ORIGIN.name
        )
        self.figures = [
            {
                "uuid": str(uuid4()),
                "country": self.country.id,
                "quantifier": Figure.QUANTIFIER.MORE_THAN.name,
                "reported": 10,
                "unit": Figure.UNIT.HOUSEHOLD.name,  # missing household_size
                "term": Figure.FIGURE_TERMS.EVACUATED.name,
                "category": Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT.name,
                "role": Figure.ROLE.RECOMMENDED.name,
                "startDate": "2020-10-10",
                "includeIdu": True,
                "excerptIdu": "excerpt abc",
                "figureCause": Crisis.CRISIS_TYPE.CONFLICT.name,
                "geoLocations": [source],
                "householdSize": 20,
                "tags": [],
                "contextOfViolence": [],
                "sources": [],
            }

        ]

    def test_should_send_notification_to_user_who_is_assigned_to_an_event(self):
        # Ref: 1
        event = EventFactory.create()
        self.force_login(self.regional_coordinator)
        self.query(
            self.set_assignee_to_event_mutation,
            variables={'event_id': event.id, 'user_id': self.monitoring_expert.id}
        )
        self.force_login(self.monitoring_expert)
        response = self.query(
            self.notification_query,
            variables={'recipient': self.monitoring_expert.id}
        )
        notification_data = json.loads(response.content)['data']['notifications']['results'][0]
        self.assertEqual(Notification.Type.EVENT_ASSIGNED.name, notification_data['type'])

    def test_should_send_notification_to_assignee_when_coordinator_clears_assignee(self):
        # Ref: 2
        event = EventFactory.create(
            assigner=self.regional_coordinator,
            assignee=self.monitoring_expert,
            countries=(self.country, )
        )
        self.force_login(self.regional_coordinator)
        self.query(
            self.clear_assignee_from_event_mutation,
            variables={'event_id': event.id}
        )
        self.force_login(self.monitoring_expert)
        response = self.query(
            self.notification_query,
            variables={'recipient': self.monitoring_expert.id}
        )
        notification_data = json.loads(response.content)['data']['notifications']['results'][0]
        self.assertEqual(Notification.Type.EVENT_ASSIGNEE_CLEARED.name, notification_data['type'])

    def test_should_send_notification_to_both_assignees_when_coordinator_changes_an_assignee(self):
        # Ref: 3
        event = EventFactory.create(
            assigner=self.admin,
            assignee=self.regional_coordinator,
            countries=(self.country, )
        )
        self.force_login(self.admin)
        self.query(
            self.set_assignee_to_event_mutation,
            variables={'event_id': event.id, 'user_id': self.monitoring_expert.id}
        )
        # Assignee cleard case
        self.force_login(self.regional_coordinator)
        response = self.query(
            self.notification_query,
            variables={'recipient': self.regional_coordinator.id}
        )
        notification_data = json.loads(response.content)['data']['notifications']['results'][0]
        self.assertEqual(Notification.Type.EVENT_ASSIGNEE_CLEARED.name, notification_data['type'])

        # Assigned case
        self.force_login(self.monitoring_expert)
        response = self.query(
            self.notification_query,
            variables={'recipient': self.monitoring_expert.id}
        )
        notification_data = json.loads(response.content)['data']['notifications']['results'][0]
        self.assertEqual(Notification.Type.EVENT_ASSIGNED.name, notification_data['type'])

    def test_should_send_notification_to_co_ordinator_when_user_self_assigns_on_an_event(self):
        # Ref: 4
        event = EventFactory.create(
            assignee=self.monitoring_expert,
            assigner=self.regional_coordinator,
            countries=(self.country, ),
        )
        self.force_login(self.monitoring_expert)
        self.query(
            self.set_self_assignee_to_event_mutation,
            variables={'event_id': event.id}
        )
        self.force_login(self.regional_coordinator)
        response = self.query(
            self.notification_query,
            variables={'recipient': self.regional_coordinator.id}
        )
        notification_data = json.loads(response.content)['data']['notifications']['results'][0]
        self.assertEqual(Notification.Type.EVENT_SELF_ASSIGNED.name, notification_data['type'])

    def test_should_send_notification_to_co_ordinator_when_user_clears_self_as_assignee(self):
        # Ref: 5
        event = EventFactory.create(
            assignee=self.monitoring_expert,
            assigner=self.regional_coordinator,
            countries=(self.country, )
        )
        self.force_login(self.monitoring_expert)
        self.query(
            self.clear_self_assignee_from_event_mutation,
            variables={'event_id': event.id}
        )
        self.force_login(self.regional_coordinator)
        response = self.query(
            self.notification_query,
            variables={'recipient': self.regional_coordinator.id}
        )
        notification_data = json.loads(response.content)['data']['notifications']['results'][0]
        self.assertEqual(Notification.Type.EVENT_ASSIGNEE_CLEARED.name, notification_data['type'])

    def test_should_send_notification_to_co_ordinator_if_figure_is_un_approved_and_event_is_signed_off_and_approved(self):
        # Ref: 7

        # Signed off case
        event = EventFactory.create(
            assignee=self.monitoring_expert,
            assigner=self.regional_coordinator,
            countries=(self.country, ),
        )
        figure = FigureFactory.create(
            event=event,
            country=self.country,
            review_status=Figure.FIGURE_REVIEW_STATUS.APPROVED,
        )
        event.review_status = Event.EVENT_REVIEW_STATUS.SIGNED_OFF
        event.save()
        self.force_login(self.monitoring_expert)
        self.query(
            self.unapprove_figure,
            variables={'id': figure.id}
        )
        self.force_login(self.regional_coordinator)
        response = self.query(
            self.notification_query,
            variables={'recipient': self.regional_coordinator.id}
        )
        notification_data = json.loads(response.content)['data']['notifications']['results'][0]
        self.assertEqual(Notification.Type.FIGURE_UNAPPROVED_IN_SIGNED_EVENT.name, notification_data['type'])

        # Approved case
        event.review_status = Event.EVENT_REVIEW_STATUS.APPROVED
        event.save()
        self.query(
            self.unapprove_figure,
            variables={'id': figure.id}
        )
        self.force_login(self.regional_coordinator)
        response = self.query(
            self.notification_query,
            variables={'recipient': self.regional_coordinator.id}
        )
        notification_data = json.loads(response.content)['data']['notifications']['results'][0]
        self.assertEqual(Notification.Type.FIGURE_UNAPPROVED_IN_APPROVED_EVENT.name, notification_data['type'])

    def test_should_send_notification_to_the_assignee_when_there_is_a_comment_on_figure_he_is_assigned_to(self):
        # Ref: 8
        event = EventFactory.create(
            assignee=self.monitoring_expert,
            assigner=self.regional_coordinator,
        )
        figure = FigureFactory.create(event=event)
        self.force_login(self.regional_coordinator)
        response = self.query(
            self.create_review_comment,
            input_data={
                'figure': figure.id,
                'event': event.id,
                'comment': 'test comment',
                'commentType': UnifiedReviewComment.REVIEW_COMMENT_TYPE.GREY.name,
            }
        )
        self.force_login(self.monitoring_expert)
        response = self.query(
            self.notification_query,
            variables={'recipient': self.monitoring_expert.id}
        )
        notification_data = json.loads(response.content)['data']['notifications']['results'][0]
        self.assertEqual(Notification.Type.REVIEW_COMMENT_CREATED.name, notification_data['type'])

    def test_should_send_notification_to_the_user_who_created_the_figure_when_assignee_comments_on_figure(self):
        # Ref: 8
        event = EventFactory.create(
            assignee=self.monitoring_expert,
            assigner=self.regional_coordinator,
        )
        figure = FigureFactory.create(event=event, created_by=self.admin)
        self.force_login(self.monitoring_expert)
        response = self.query(
            self.create_review_comment,
            input_data={
                'figure': figure.id,
                'event': event.id,
                'comment': 'test comment',
                'commentType': UnifiedReviewComment.REVIEW_COMMENT_TYPE.GREEN.name,
            }
        )
        self.force_login(self.admin)
        response = self.query(
            self.notification_query,
            variables={'recipient': self.admin.id}
        )
        notification_data = json.loads(response.content)['data']['notifications']['results'][0]
        self.assertEqual(Notification.Type.REVIEW_COMMENT_CREATED.name, notification_data['type'])

    def test_should_send_notification_to_the_assignee_when_there_is_a_re_request_review(self):
        # Ref: 10
        event = EventFactory.create(
            assignee=self.monitoring_expert,
            assigner=self.regional_coordinator,
        )
        figure = FigureFactory.create(event=event)
        self.force_login(self.regional_coordinator)
        self.query(
            self.re_request_review_figure,
            variables={'id': figure.id}
        )
        self.force_login(self.monitoring_expert)
        response = self.query(
            self.notification_query,
            variables={'recipient': self.monitoring_expert.id}
        )
        notification_data = json.loads(response.content)['data']['notifications']['results'][0]
        self.assertEqual(Notification.Type.FIGURE_RE_REQUESTED_REVIEW.name, notification_data['type'])

    def test_should_send_notification_to_the_coordinators_and_who_created_event_when_event_is_approved(self):
        # Ref: 11
        event = EventFactory.create(
            assignee=self.monitoring_expert,
            assigner=self.regional_coordinator,
            countries=(self.country, ),
            created_by=self.admin,
        )
        figure = FigureFactory.create(event=event, review_status=Figure.FIGURE_REVIEW_STATUS.REVIEW_IN_PROGRESS)
        self.force_login(self.monitoring_expert)
        self.query(
            self.approve_figure,
            variables={'id': figure.id}
        )
        # Regional coordinator should receive notification
        self.force_login(self.regional_coordinator)
        response = self.query(
            self.notification_query,
            variables={'recipient': self.regional_coordinator.id}
        )
        notification_data = json.loads(response.content)['data']['notifications']['results'][0]
        self.assertEqual(Notification.Type.EVENT_APPROVED.name, notification_data['type'])

        # Admin who is creator should receive notification
        self.force_login(self.admin)
        response = self.query(
            self.notification_query,
            variables={'recipient': self.admin.id}
        )
        notification_data = json.loads(response.content)['data']['notifications']['results'][0]
        self.assertEqual(Notification.Type.EVENT_APPROVED.name, notification_data['type'])

    def test_should_send_notification_to_co_ordinator_if_event_is_signed_off(self):
        # Ref: 12
        event = EventFactory.create(
            assignee=self.monitoring_expert,
            assigner=self.regional_coordinator,
            countries=(self.country, ),
            review_status=Event.EVENT_REVIEW_STATUS.APPROVED,
        )
        self.force_login(self.admin)
        self.query(
            self.sign_off_event,
            variables={'event_id': event.id}
        )
        self.force_login(self.regional_coordinator)
        response = self.query(
            self.notification_query,
            variables={'recipient': self.regional_coordinator.id}
        )
        notification_data = json.loads(response.content)['data']['notifications']['results'][0]
        self.assertEqual(Notification.Type.EVENT_SIGNED_OFF.name, notification_data['type'])

    def test_should_send_notification_to_assignee_if_figure_is_added_edited_deleted_and_event_is_approved(self):
        # Ref: 13
        event = EventFactory.create(
            assignee=self.monitoring_expert,
            assigner=self.regional_coordinator,
            countries=(self.country, ),
            review_status=Event.EVENT_REVIEW_STATUS.APPROVED,
        )
        entry = EntryFactory.create()
        FigureFactory.create(
            event=event,
            review_status=Figure.FIGURE_REVIEW_STATUS.APPROVED,
            entry=entry,
        )

        # Create figure in already approved event
        self.force_login(self.admin)
        figures = self.figures
        figures[0]['event'] = event.id

        response = self.query(
            self.create_update_figure,
            input_data={
                'id': entry.id,
                'figures': figures
            }
        )
        content = json.loads(response.content)
        figure_id = content['data']['updateEntry']['result']['figures'][0]['id']

        self.force_login(self.regional_coordinator)
        response = self.query(
            self.notification_query,
            variables={'recipient': self.regional_coordinator.id}
        )
        notification_data = json.loads(response.content)['data']['notifications']['results'][0]
        self.assertEqual(Notification.Type.FIGURE_CREATED_IN_APPROVED_EVENT.name, notification_data['type'])

        # Update figure in already approved event
        event.review_status = Event.EVENT_REVIEW_STATUS.APPROVED
        event.save()

        self.force_login(self.admin)
        figures = self.figures
        figures[0]['id'] = figure_id
        response = self.query(
            self.create_update_figure,
            input_data={
                'id': entry.id,
                'figures': figures
            }
        )
        self.force_login(self.regional_coordinator)
        response = self.query(
            self.notification_query,
            variables={'recipient': self.regional_coordinator.id}
        )
        notification_data = json.loads(response.content)['data']['notifications']['results'][0]
        self.assertEqual(Notification.Type.FIGURE_UPDATED_IN_APPROVED_EVENT.name, notification_data['type'])

        # Delete figure
        event.review_status = Event.EVENT_REVIEW_STATUS.APPROVED
        event.save()

        self.query(
            self.delete_figure,
            variables={
                'id': figure_id,
            }
        )
        response = self.query(
            self.notification_query,
            variables={'recipient': self.regional_coordinator.id}
        )
        notification_data = json.loads(response.content)['data']['notifications']['results'][0]
        self.assertEqual(Notification.Type.FIGURE_DELETED_IN_APPROVED_EVENT.name, notification_data['type'])
        self.assertEqual(str(entry.id), notification_data['entry']['id'])

    def test_should_send_notification_to_co_ordinator_if_figure_is_added_edited_deleted_in_signed_off_event(self):
        # Ref: 14
        event = EventFactory.create(
            assignee=self.monitoring_expert,
            assigner=self.regional_coordinator,
            countries=(self.country, ),
            review_status=Event.EVENT_REVIEW_STATUS.SIGNED_OFF,
        )
        entry = EntryFactory.create()
        self.force_login(self.regional_coordinator)
        figures = self.figures
        figures[0]['event'] = event.id

        # Create figure
        response = self.query(
            self.create_update_figure,
            input_data={
                'id': entry.id,
                'figures': figures
            }
        )
        content = json.loads(response.content)
        figure_id = content['data']['updateEntry']['result']['figures'][0]['id']

        response = self.query(
            self.notification_query,
            variables={'recipient': self.regional_coordinator.id}
        )
        notification_data = json.loads(response.content)['data']['notifications']['results'][0]
        self.assertEqual(Notification.Type.FIGURE_CREATED_IN_SIGNED_EVENT.name, notification_data['type'])

        # Update figure
        event.review_status = Event.EVENT_REVIEW_STATUS.SIGNED_OFF
        event.save()

        figures[0]['id'] = figure_id
        self.query(
            self.create_update_figure,
            input_data={
                'id': entry.id,
                'figures': figures,
            }
        )
        response = self.query(
            self.notification_query,
            variables={'recipient': self.regional_coordinator.id}
        )
        notification_data = json.loads(response.content)['data']['notifications']['results'][0]
        self.assertEqual(Notification.Type.FIGURE_UPDATED_IN_SIGNED_EVENT.name, notification_data['type'])

        # Delete figure
        event.review_status = Event.EVENT_REVIEW_STATUS.SIGNED_OFF
        event.save()
        response = self.query(
            self.delete_figure,
            variables={
                'id': figure_id,
            }
        )
        print(json.loads(response.content))
        response = self.query(
            self.notification_query,
            variables={'recipient': self.regional_coordinator.id}
        )
        notification_data = json.loads(response.content)['data']['notifications']['results'][0]
        self.assertEqual(Notification.Type.FIGURE_DELETED_IN_SIGNED_EVENT.name, notification_data['type'])
        self.assertEqual(str(entry.id), notification_data['entry']['id'])

    def test_should_send_notification_when_include_triangulation_in_qa_has_changed(self):
        # Ref: 15
        self.force_login(self.regional_coordinator)
        event = EventFactory.create(
            assignee=self.monitoring_expert,
            assigner=self.regional_coordinator,
            countries=(self.country, )
        )
        self.query(
            self.update_event,
            input_data={
                'id': event.id,
                'includeTriangulationInQa': True
            }
        )
        response = self.query(
            self.notification_query,
            variables={'recipient': self.regional_coordinator.id}
        )
        notification_data = json.loads(response.content)['data']['notifications']['results'][0]
        self.assertEqual(Notification.Type.EVENT_INCLUDE_TRIANGULATION_CHANGED.name, notification_data['type'])

    def test_can_toggle_read_and_unread_notification(self):
        notification = NotificationFactory.create(
            is_read=False,
            recipient=self.regional_coordinator,
            type=Notification.Type.FIGURE_CREATED_IN_APPROVED_EVENT,
        )
        # Read case
        self.force_login(self.regional_coordinator)
        response = self.query(
            self.toggle_notificaiton_read,
            variables={
                'id': notification.id,
            }
        )
        notification_data = json.loads(response.content)['data']['toggleNotificationRead']['result']
        self.assertEqual(notification_data['id'], str(notification.id))
        self.assertEqual(True, notification_data['isRead'])

        # Unread case
        response = self.query(
            self.toggle_notificaiton_read,
            variables={
                'id': notification.id,
            }
        )
        notification_data = json.loads(response.content)['data']['toggleNotificationRead']['result']
        self.assertEqual(notification_data['id'], str(notification.id))
        self.assertEqual(False, notification_data['isRead'])
