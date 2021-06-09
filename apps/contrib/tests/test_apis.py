import json
import magic

from django.core.files.temp import NamedTemporaryFile

from apps.contrib.models import Attachment
from apps.users.enums import USER_ROLE
from utils.tests import HelixGraphQLTestCase, create_user_with_role


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
