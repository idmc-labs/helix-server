import json
import magic

from django.core.files.temp import NamedTemporaryFile

from utils.tests import HelixGraphQLTestCase, create_user_with_role
from utils.factories import FigureFactory, EventFactory, CountryFactory
from apps.contrib.models import Attachment
from apps.event.models import Figure
from apps.users.enums import USER_ROLE
from apps.contrib.models import BulkApiOperation


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
    Mutation = '''
        mutation ($data: BulkApiOperationInputType!) {
          triggerBulkOperation(data: $data) {
            ok
            errors
            result {
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
                        filterCreatedBy
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
              successCount
              failureCount
            }
          }
        }
    '''

    def setUp(self) -> None:
        self.editor = create_user_with_role(USER_ROLE.MONITORING_EXPERT.name)
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

        def _generate_payload(update_role, **filters):
            return {
                'data': {
                    'action': BulkApiOperation.BULK_OPERATION_ACTION.FIGURE_ROLE.name,
                    'filters': {
                        'figureRole': {
                            'figure': {
                                'filterCreatedBy': [str(self.editor.pk)],
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

        def _basic_check(_variables, _content, success_count, failure_count, errors):
            self.assertTrue(_content['ok'], _content)
            self.assertIsNone(_content['errors'])
            self.assertIsNotNone(_content['result'])
            self.assertEqual(_content['result']['filters'], _variables['data']['filters'])
            self.assertEqual(_content['result']['payload'], _variables['data']['payload'])

            operation = BulkApiOperation.objects.get(pk=_content['result']['id'])
            self.assertEqual(operation.success_count, success_count)
            self.assertEqual(operation.failure_count, failure_count)
            self.assertEqual(operation.errors, errors)

        # Try 1
        assert Figure.objects.filter(role=Figure.ROLE.TRIANGULATION).count() == 3
        assert Figure.objects.filter(role=Figure.ROLE.RECOMMENDED).count() == 1
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
        _basic_check(variables, content, 3, 0, [None] * 3)
        assert Figure.objects.filter(role=Figure.ROLE.TRIANGULATION).count() == 0
        assert Figure.objects.filter(role=Figure.ROLE.RECOMMENDED).count() == 4

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
        _basic_check(variables, content, 0, 0, [])
        assert Figure.objects.filter(role=Figure.ROLE.TRIANGULATION).count() == 0
        assert Figure.objects.filter(role=Figure.ROLE.RECOMMENDED).count() == 4

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
        _basic_check(variables, content, 4, 0, [None] * 4)
        assert Figure.objects.filter(role=Figure.ROLE.TRIANGULATION).count() == 4
        assert Figure.objects.filter(role=Figure.ROLE.RECOMMENDED).count() == 0

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
        _basic_check(variables, content, 2, 0, [None] * 2)
        assert Figure.objects.filter(role=Figure.ROLE.TRIANGULATION).count() == 2
        assert Figure.objects.filter(role=Figure.ROLE.RECOMMENDED).count() == 2
