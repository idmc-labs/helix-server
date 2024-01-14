import json
import typing
import datetime
import magic
from unittest.mock import patch

from django.core.files.temp import NamedTemporaryFile
# from rest_framework import serializers

from utils.tests import HelixGraphQLTestCase, create_user_with_role
from utils.factories import FigureFactory, EventFactory, CountryFactory
from apps.contrib.models import Attachment
from apps.event.models import Figure
from apps.users.enums import USER_ROLE
from apps.contrib.models import BulkApiOperation
from apps.contrib.bulk_operations.tasks import run_bulk_api_operation


# def _raise(expection: Exception):
#     raise expection


class TestAttachment(HelixGraphQLTestCase):
    def setUp(self) -> None:
        self.editor = create_user_with_role(USER_ROLE.MONITORING_EXPERT.name)
        self.mutation = """
            mutation ($data: AttachmentCreateInputType!) {
              createAttachment(data: $data) {
                ok
                errors
                result {
                  attachment
                  attachmentFor
                  createdAt
                  id
                  modifiedAt
                  mimetype
                  encoding
                  filetypeDetail
                }
              }
            }
        """
        self.variables = {
            "data": {"attachmentFor": Attachment.FOR_CHOICES.ENTRY, "attachment": None}
        }
        self.force_login(self.editor)

    def test_create_attachment(self):
        file_text = b'fake blaa'
        with NamedTemporaryFile() as t_file:
            t_file.write(file_text)
            t_file.seek(0)
            response = self._client.post(
                '/graphql',
                data={
                    'operations': json.dumps({
                        'query': self.mutation,
                        'variables': self.variables
                    }),
                    't_file': t_file,
                    'map': json.dumps({
                        't_file': ['variables.data.attachment']
                    })
                }
            )
        content = response.json()
        self.assertResponseNoErrors(response)
        self.assertTrue(content['data']['createAttachment']['ok'], content)
        self.assertIsNotNone(content['data']['createAttachment']['result']['id'])
        self.assertIsNotNone(content['data']['createAttachment']['result']['attachment'])
        with magic.Magic(flags=magic.MAGIC_MIME_TYPE) as m:
            self.assertEqual(content['data']['createAttachment']['result']['mimetype'],
                             m.id_buffer(file_text))
        with magic.Magic(flags=magic.MAGIC_MIME_ENCODING) as m:
            self.assertEqual(content['data']['createAttachment']['result']['encoding'],
                             m.id_buffer(file_text))
        with magic.Magic() as m:
            self.assertEqual(content['data']['createAttachment']['result']['filetypeDetail'],
                             m.id_buffer(file_text))


class TestBulkOperation(HelixGraphQLTestCase):
    BulkApiOperationObjectFragment = '''
        fragment BulkApiOperationObjectResponse on BulkApiOperationObjectType {
            id
            createdAt
            createdBy {
              id
            }
            action
            actionDisplay
            status
            statusDisplay
            filters {
              figureRole {
                  figure {
                      filterFigureCreatedBy
                      filterFigureRoles
                      filterFigureIds
                  }
              }
            }
            payload {
              figureRole {
                  role
              }
            }
            startedAt
            completedAt
            successCount
            failureCount
            successList {
              id
              frontendUrl
              frontendPermalinkUrl
            }
            failureList {
              id
              frontendUrl
              frontendPermalinkUrl
              errors
            }
        }
    '''

    Mutation = BulkApiOperationObjectFragment + '''\n
        mutation ($data: BulkApiOperationInputType!) {
          triggerBulkOperation(data: $data) {
            ok
            errors
            result {
                ...BulkApiOperationObjectResponse
            }
          }
        }
    '''

    Query = BulkApiOperationObjectFragment + '''\n
        query ($id: ID!) {
          bulkApiOperation(id: $id) {
            ...BulkApiOperationObjectResponse
          }
        }
    '''

    def setUp(self) -> None:
        self.editor = create_user_with_role(USER_ROLE.MONITORING_EXPERT.name)
        self.guest = create_user_with_role(USER_ROLE.GUEST.name)
        self.another_editor = create_user_with_role(USER_ROLE.MONITORING_EXPERT.name)
        self.country = CountryFactory.create()
        self.event = EventFactory.create(created_by=self.editor)
        self.event.countries.set([self.country])
        self.figure_kwargs = dict(
            event=self.event,
            country=self.country,
            created_by=self.editor,
            category=Figure.FIGURE_CATEGORY_TYPES.IDPS,
        )
        self.force_login(self.editor)

    def test_bulk_figure_role(self):
        fig1, fig2, fig3 = FigureFactory.create_batch(3, **self.figure_kwargs, role=Figure.ROLE.TRIANGULATION)
        fig4 = FigureFactory.create(**self.figure_kwargs, role=Figure.ROLE.RECOMMENDED)
        FigureFactory.create(
            **{
                **self.figure_kwargs,
                'created_by': self.another_editor,
            },
            role=Figure.ROLE.RECOMMENDED,
        )

        def _generate_payload(update_role, **filters):
            return {
                'data': {
                    'action': BulkApiOperation.BULK_OPERATION_ACTION.FIGURE_ROLE.name,
                    'filters': {
                        'figureRole': {
                            'figure': {
                                'filterFigureCreatedBy': [str(self.editor.pk)],
                                **filters,
                            }
                        },
                    },
                    'payload': {
                        'figureRole': {
                            'role': update_role.name,
                        },
                    },
                },
            }

        def _basic_check(
            _variables: dict,
            _content: dict,
            expected_success: typing.List[Figure],
            expected_failure: typing.List[Figure],
        ):
            self.assertTrue(_content['ok'], _content)
            self.assertIsNone(_content['errors'])
            self.assertIsNotNone(_content['result'])
            self.assertEqual(_variables['data']['filters'], _content['result']['filters'])
            self.assertEqual(_variables['data']['payload'], _content['result']['payload'])

            operation = BulkApiOperation.objects.get(pk=_content['result']['id'])
            self.assertEqual(BulkApiOperation.BULK_OPERATION_STATUS.COMPLETED, operation.status)
            self.assertEqual(
                {'success_count': len(expected_success), 'failure_count': len(expected_failure)},
                {'success_count': operation.success_count, 'failure_count': operation.failure_count}
            )

            # Re-fetch from GraphQl
            update_content = self.query(
                self.Query,
                variables={'id': operation.pk},
            ).json()['data']['bulkApiOperation']
            success_list = update_content['successList']
            failure_list = update_content['failureList']
            self.assertEqual(len(expected_success), len(success_list))
            self.assertEqual(len(expected_failure), len(failure_list))

            def _generate_frontend_url(figure):
                return {
                    'frontendPermalinkUrl': f'/figures/{figure.event_id}/{figure.pk}',
                    'frontendUrl': f'/entries/{figure.event_id}/?id={figure.pk}#/figures-and-analysis',
                }

            # Check for success/failure response
            if operation.success_count > 0:
                self.assertEqual([
                    {
                        'id': str(figure.pk),
                        **_generate_frontend_url(figure),
                    }
                    for figure in expected_success
                ], success_list)
            if operation.failure_count > 0:
                self.assertEqual([
                    {
                        'id': str(figure.pk),
                        **_generate_frontend_url(figure),
                        'errors': [],
                    }
                    for figure in expected_failure
                ], failure_list)

            self.assertIsNotNone(operation.snapshot)

        figure_qs = Figure.objects.filter(created_by=self.editor)
        # Try 0 - Invalid request
        variables = {
            'data': {
                'action': BulkApiOperation.BULK_OPERATION_ACTION.FIGURE_ROLE.name,
                'filters': {},
                'payload': {},
            }
        }
        with self.captureOnCommitCallbacks(execute=True):
            response = self.query(self.Mutation, variables=variables)
        self.assertResponseNoErrors(response)
        content = response.json()['data']['triggerBulkOperation']
        assert content['ok'] is False
        assert len(content['errors']) == 2

        # Try 1
        assert figure_qs.filter(role=Figure.ROLE.TRIANGULATION).count() == 3
        assert figure_qs.filter(role=Figure.ROLE.RECOMMENDED).count() == 1
        variables = _generate_payload(
            Figure.ROLE.RECOMMENDED,
            # Filters
            filterFigureIds=None,
            filterFigureRoles=[Figure.ROLE.TRIANGULATION.name],
        )
        with self.captureOnCommitCallbacks(execute=True):
            response = self.query(self.Mutation, variables=variables)
        self.assertResponseNoErrors(response)
        content = response.json()['data']['triggerBulkOperation']
        _basic_check(variables, content, [fig1, fig2, fig3], [])
        assert figure_qs.filter(role=Figure.ROLE.TRIANGULATION).count() == 0
        assert figure_qs.filter(role=Figure.ROLE.RECOMMENDED).count() == 4

        # Try 2
        variables = _generate_payload(
            Figure.ROLE.RECOMMENDED,
            # Filters
            filterFigureIds=None,
            filterFigureRoles=[Figure.ROLE.TRIANGULATION.name],
        )
        with self.captureOnCommitCallbacks(execute=True):
            response = self.query(self.Mutation, variables=variables)
        self.assertResponseNoErrors(response)
        content = response.json()['data']['triggerBulkOperation']
        _basic_check(variables, content, [], [])
        assert figure_qs.filter(role=Figure.ROLE.TRIANGULATION).count() == 0
        assert figure_qs.filter(role=Figure.ROLE.RECOMMENDED).count() == 4

        # Try 3
        variables = _generate_payload(
            Figure.ROLE.TRIANGULATION,
            # Filters
            filterFigureIds=None,
            filterFigureRoles=[Figure.ROLE.RECOMMENDED.name],
        )
        with self.captureOnCommitCallbacks(execute=True):
            response = self.query(self.Mutation, variables=variables)
        self.assertResponseNoErrors(response)
        content = response.json()['data']['triggerBulkOperation']
        _basic_check(variables, content, [fig1, fig2, fig3, fig4], [])
        assert figure_qs.filter(role=Figure.ROLE.TRIANGULATION).count() == 4
        assert figure_qs.filter(role=Figure.ROLE.RECOMMENDED).count() == 0

        # Try 3 - With explicit ids
        variables = _generate_payload(
            Figure.ROLE.RECOMMENDED,
            # Filters
            filterFigureIds=[str(fig1.pk), str(fig4.pk)],
            filterFigureRoles=None,
        )
        with self.captureOnCommitCallbacks(execute=True):
            response = self.query(self.Mutation, variables=variables)
        self.assertResponseNoErrors(response)
        content = response.json()['data']['triggerBulkOperation']
        _basic_check(variables, content, [fig1, fig4], [])
        assert figure_qs.filter(role=Figure.ROLE.TRIANGULATION).count() == 2
        assert figure_qs.filter(role=Figure.ROLE.RECOMMENDED).count() == 2

        # Try 4 - Without permission
        self.force_login(self.guest)
        variables = _generate_payload(
            Figure.ROLE.RECOMMENDED,
            # Filters
            filterFigureIds=[str(fig1.pk), str(fig4.pk)],
            filterFigureRoles=None,
        )
        with self.captureOnCommitCallbacks(execute=True):
            response = self.query(self.Mutation, variables=variables)
        self.assertResponseNoErrors(response)
        content = response.json()['data']['triggerBulkOperation']
        _basic_check(variables, content, [], [])
        assert figure_qs.filter(role=Figure.ROLE.TRIANGULATION).count() == 2
        assert figure_qs.filter(role=Figure.ROLE.RECOMMENDED).count() == 2
        self.force_login(self.editor)

        # TODO: # Try 5 - With mock validation error
        # variables = _generate_payload(
        #     Figure.ROLE.RECOMMENDED,
        #     # Filters
        #     filterFigureIds=[str(fig1.pk), str(fig4.pk)],
        #     filterFigureRoles=None,
        # )
        # with self.captureOnCommitCallbacks(execute=True):
        #     with patch(
        #         'apps.entry.mutations.BulkUpdateFigures.serializer_class.update',
        #         side_effect=lambda *_: _raise(serializers.ValidationError('Random error')),
        #     ):
        #         response = self.query(self.Mutation, variables=variables)
        # self.assertResponseNoErrors(response)
        # content = response.json()['data']['triggerBulkOperation']
        # _basic_check(variables, content, [], [fig1, fig4])
        # assert figure_qs.filter(role=Figure.ROLE.TRIANGULATION).count() == 2
        # assert figure_qs.filter(role=Figure.ROLE.RECOMMENDED).count() == 2

        # Try 6 - background task will not run
        variables = _generate_payload(
            Figure.ROLE.TRIANGULATION,
            # Filters
            filterFigureIds=None,
            filterFigureRoles=None,
        )
        response = self.query(self.Mutation, variables=variables)
        self.assertResponseNoErrors(response)
        content = response.json()['data']['triggerBulkOperation']
        assert content['result']['id'] is not None
        operation = BulkApiOperation.objects.get(pk=content['result']['id'])
        operation.created_at = (
            operation.created_at - datetime.timedelta(minutes=BulkApiOperation.WAIT_TIME_THRESHOLD_IN_MINUTES)
        )
        # Run the task manually which should cancel the operation
        run_bulk_api_operation(operation)
        operation.refresh_from_db()
        assert operation.status == BulkApiOperation.BULK_OPERATION_STATUS.KILLED
        del operation

        # Try 7 - threshold count check
        with patch(
            'apps.contrib.bulk_operations.serializers.BulkApiOperation.QUERYSET_COUNT_THRESHOLD',
            1,
        ):
            variables = _generate_payload(
                Figure.ROLE.RECOMMENDED,
                # Filters
                filterFigureIds=[str(fig1.pk), str(fig4.pk)],
            )
            with self.captureOnCommitCallbacks(execute=True):
                response = self.query(self.Mutation, variables=variables)
            self.assertResponseNoErrors(response)
            content = response.json()['data']['triggerBulkOperation']
            assert content['ok'] is False, content
            assert (
                content['errors'][0]['messages'] ==
                'Bulk update should include less then 1. Current count is 2'
            ), content

        # This shouldn't change at all
        assert figure_qs.filter(role=Figure.ROLE.TRIANGULATION).count() == 2
        assert figure_qs.filter(role=Figure.ROLE.RECOMMENDED).count() == 2
