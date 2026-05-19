"""
End-to-end tests for the ``triggerHulkBulkImport`` mutation.

Goal: prove the wire-up — multipart-style file uploads land on
``HulkBulkImportDataset`` rows, the task is dispatched on commit (eager celery
makes this synchronous in tests), and the resulting model exposes the
per-dataset success/failure file URLs via GraphQL.

The handler itself is mocked here so we don't depend on real helix mutation
validity for these end-to-end tests — that surface is covered in
``test_handler.py``.
"""

from __future__ import annotations

import json
from io import BytesIO
from unittest.mock import patch

from django.contrib.auth.models import Permission

from apps.hulk.models import HulkBulkImport, HulkBulkImportDataset
from apps.users.enums import USER_ROLE
from utils.factories import (
    CountryFactory,
    DisasterSubTypeFactory,
    OrganizationFactory,
    OtherSubtypeFactory,
    ViolenceSubTypeFactory,
)
from utils.tests import HelixGraphQLTestCase, create_user_with_role

from .fixtures import FixtureContext, build_jsonl_bundle


def _make_ctx() -> FixtureContext:
    return FixtureContext(
        country_id=CountryFactory.create(iso2="NP", iso3="NPL", idmc_short_name="Nepal").id,
        publisher_id=OrganizationFactory.create().id,
        source_id=OrganizationFactory.create().id,
        violence_sub_type_id=ViolenceSubTypeFactory.create().id,
        disaster_sub_type_id=DisasterSubTypeFactory.create().id,
        other_sub_type_id=OtherSubtypeFactory.create().id,
    )


def _bytes_io(payload: bytes, filename: str) -> BytesIO:
    f = BytesIO(payload)
    f.name = filename
    return f


# Resource short name → GraphQL enum value the mutation accepts.
_TYPE_FOR_RESOURCE = {
    "attachments": "ATTACHMENT",
    "source_previews": "SOURCE_PREVIEW",
    "entries": "ENTRY",
    "events": "EVENT",
    "figures": "FIGURE",
}


class TestTriggerHulkBulkImport(HelixGraphQLTestCase):
    MUTATION = """
        mutation ($data: HulkBulkImportCreateInputType!) {
          triggerHulkBulkImport(data: $data) {
            ok
            errors
            result {
              id
              status
              successCount
              failureCount
              datasets {
                importType
                successCount
                failureCount
              }
            }
          }
        }
    """

    def setUp(self):
        self.admin = create_user_with_role(USER_ROLE.ADMIN.name)
        # The bulk-import permission is intentionally *not* baked into any
        # role — admins grant it per-user via the Django admin panel.
        self.admin.user_permissions.add(
            Permission.objects.get(codename="trigger_hulkbulkimport"),
        )
        self.bundle = build_jsonl_bundle(_make_ctx())

    def _post_with_datasets(
        self,
        resources: list[str],
        *,
        bundle: dict | None = None,
        extra_data: dict | None = None,
    ):
        """
        Build a multipart triggerHulkBulkImport request with one ``datasets``
        entry per ``resources`` short name. Each file slot points at
        ``variables.data.datasets.<i>.importFile``.
        """
        bundle = bundle or self.bundle
        datasets = [{"importType": _TYPE_FOR_RESOURCE[r], "importFile": None} for r in resources]
        data_var = {"datasets": datasets}
        if extra_data:
            data_var.update(extra_data)
        operations = json.dumps({"query": self.MUTATION, "variables": {"data": data_var}})
        file_map = {f"f{i}": [f"variables.data.datasets.{i}.importFile"] for i in range(len(resources))}
        body: dict = {"operations": operations, "map": json.dumps(file_map)}
        for i, r in enumerate(resources):
            body[f"f{i}"] = _bytes_io(bundle[r], f"{r}.jsonl")
        return self._client.post("/graphql", data=body)

    def test_mutation_requires_authentication(self):
        # No login.
        resp = self._post_with_datasets(["events"])
        content = resp.json()
        # ``@is_authenticated`` raises PermissionDenied → graphql top-level error,
        # so ``data.triggerHulkBulkImport`` resolves to null.
        self.assertIsNone(content["data"]["triggerHulkBulkImport"])

    def test_mutation_requires_bulk_import_permission(self):
        # ADMIN role alone is not enough — the bulk_import permission must be
        # attached to the user explicitly via the admin panel.
        user = create_user_with_role(USER_ROLE.ADMIN.name)
        self.force_login(user)
        resp = self._post_with_datasets(["events"])
        content = resp.json()
        self.assertIsNone(content["data"]["triggerHulkBulkImport"])

    def test_mutation_requires_at_least_one_dataset(self):
        self.force_login(self.admin)
        # Empty datasets list.
        resp = self.query(self.MUTATION, variables={"data": {"datasets": []}})
        content = resp.json()
        self.assertFalse(content["data"]["triggerHulkBulkImport"]["ok"])
        errors = content["data"]["triggerHulkBulkImport"]["errors"] or []
        flat = {e.get("field") for e in errors}
        # Either the field-level ``datasets`` error or the serializer-level rollup.
        self.assertTrue("datasets" in flat or "nonFieldErrors" in flat, content)

    def test_mutation_rejects_duplicate_import_type(self):
        self.force_login(self.admin)
        resp = self._post_with_datasets(["events", "events"])
        content = resp.json()
        self.assertFalse(content["data"]["triggerHulkBulkImport"]["ok"], content)
        # The duplicate guard surfaces under the ``datasets`` field.
        errors = content["data"]["triggerHulkBulkImport"]["errors"] or []
        joined = json.dumps(errors)
        self.assertIn("Duplicate dataset", joined)

    def test_mutation_creates_bulk_import_and_runs_handler(self):
        self.force_login(self.admin)
        with patch(
            "apps.hulk.bulk.handler.HulkBulkImportHandler.handle", return_value=True
        ) as mock_handle, self.captureOnCommitCallbacks(execute=True):
            resp = self._post_with_datasets(
                ["attachments", "source_previews", "entries", "events", "figures"],
            )
        content = resp.json()
        self.assertResponseNoErrors(resp)
        self.assertTrue(content["data"]["triggerHulkBulkImport"]["ok"], content)
        result = content["data"]["triggerHulkBulkImport"]["result"]
        self.assertIsNotNone(result["id"])

        bulk = HulkBulkImport.objects.get(pk=result["id"])
        self.assertEqual(bulk.datasets.count(), 5)
        # Every dataset row has its import_file populated.
        for ds in bulk.datasets.all():
            self.assertTrue(bool(ds.import_file))

        mock_handle.assert_called_once()

    def test_mutation_rejects_when_active_import_exists(self):
        """Global lock: another PENDING/IN_PROGRESS row blocks new creation."""
        self.force_login(self.admin)
        # Seed a PENDING bulk import. The serializer should refuse to queue
        # another one until this row leaves PENDING/IN_PROGRESS.
        HulkBulkImport.objects.create(created_by=self.admin)
        resp = self._post_with_datasets(["events"])
        content = resp.json()
        self.assertFalse(content["data"]["triggerHulkBulkImport"]["ok"], content)
        errors = content["data"]["triggerHulkBulkImport"]["errors"] or []
        joined = json.dumps(errors)
        self.assertIn("Another hulk bulk import", joined)

    def test_mutation_partial_payload(self):
        """Submitting only one dataset should be accepted."""
        self.force_login(self.admin)
        with patch("apps.hulk.bulk.handler.HulkBulkImportHandler.handle", return_value=True), self.captureOnCommitCallbacks(
            execute=True
        ):
            resp = self._post_with_datasets(["events"])
        content = resp.json()
        self.assertResponseNoErrors(resp)
        self.assertTrue(content["data"]["triggerHulkBulkImport"]["ok"], content)
        bulk = HulkBulkImport.objects.get(pk=content["data"]["triggerHulkBulkImport"]["result"]["id"])
        self.assertEqual(bulk.datasets.count(), 1)
        self.assertEqual(
            bulk.datasets.first().import_type,
            HulkBulkImportDataset.HULK_BULK_IMPORT_DATASET_IMPORT_TYPE.EVENT,
        )

    def test_attachment_only_payload_runs_through_real_attachment_mutation(self):
        """
        End-to-end smoke test for the attachment multipart path:

        1. Client POSTs ``triggerHulkBulkImport`` with only the attachments
           dataset via the standard multipart-upload pattern.
        2. The on-commit celery task runs the handler synchronously
           (CELERY_TASK_ALWAYS_EAGER).
        3. The attachment handler downloads each row's ``file_url`` (patched
           here so we don't hit the network) and calls the real
           ``createAttachment`` GraphQL mutation.
        4. Result: the attachments dataset's ``success_file`` has one
           ``{uuid, id, message}`` row per fixture attachment, each pointing
           at a live Attachment.
        """
        from django.core.files.uploadedfile import SimpleUploadedFile

        from apps.contrib.models import Attachment

        def _fake_download(_url):
            return SimpleUploadedFile(
                name="dummy.pdf",
                content=b"%PDF-1.1\n%%EOF\n",
                content_type="application/pdf",
            )

        self.force_login(self.admin)
        with patch("apps.hulk.bulk.handler.download_file", side_effect=_fake_download), self.captureOnCommitCallbacks(
            execute=True
        ):
            resp = self._post_with_datasets(["attachments"])
        content = resp.json()
        self.assertResponseNoErrors(resp)
        self.assertTrue(content["data"]["triggerHulkBulkImport"]["ok"], content)
        result = content["data"]["triggerHulkBulkImport"]["result"]
        bulk = HulkBulkImport.objects.get(pk=result["id"])

        self.assertEqual(bulk.status, HulkBulkImport.HULK_BULK_IMPORT_STATUS.COMPLETED)
        ds = bulk.datasets.get(import_type=HulkBulkImportDataset.HULK_BULK_IMPORT_DATASET_IMPORT_TYPE.ATTACHMENT.value)
        self.assertGreater(ds.success_count or 0, 0)

        success_lines = ds.success_file.open("rb").read().decode("utf-8").splitlines()
        ds.success_file.close()
        rows = [json.loads(line) for line in success_lines if line]
        for row in rows:
            self.assertEqual(row["message"], "Created")
            self.assertTrue(Attachment.objects.filter(pk=row["id"]).exists())


class TestHulkBulkImportQuery(HelixGraphQLTestCase):
    QUERY = """
        query ($id: ID!) {
          hulkBulkImport(id: $id) { id status }
        }
    """

    def setUp(self):
        self.owner = create_user_with_role(USER_ROLE.ADMIN.name)
        self.viewer = create_user_with_role(USER_ROLE.ADMIN.name)
        self.bulk = HulkBulkImport.objects.create(created_by=self.owner)

    def _post(self, user):
        if user is not None:
            self.force_login(user)
        return self.query(self.QUERY, variables={"id": self.bulk.id})

    def test_query_requires_authentication(self):
        content = self._post(None).json()
        self.assertIsNone(content["data"]["hulkBulkImport"])

    def test_query_allowed_for_any_authenticated_user(self):
        # Reads are open to anyone authenticated — no trigger permission needed,
        # and viewers can see bulks they didn't create.
        resp = self._post(self.viewer)
        self.assertResponseNoErrors(resp)
        self.assertEqual(resp.json()["data"]["hulkBulkImport"]["id"], str(self.bulk.id))


class TestHulkBulkImportListQuery(HelixGraphQLTestCase):
    QUERY = """
        query ($filters: HulkBulkImportFilterDataInputType) {
          hulkBulkImports(filters: $filters) {
            totalCount
            results { id status }
          }
        }
    """

    def setUp(self):
        self.owner = create_user_with_role(USER_ROLE.ADMIN.name)
        self.viewer = create_user_with_role(USER_ROLE.ADMIN.name)
        self.bulk_a = HulkBulkImport.objects.create(created_by=self.owner)
        self.bulk_b = HulkBulkImport.objects.create(
            created_by=self.owner,
            status=HulkBulkImport.HULK_BULK_IMPORT_STATUS.COMPLETED,
        )
        self.bulk_c = HulkBulkImport.objects.create(created_by=self.viewer)

    def _post(self, user, variables=None):
        if user is not None:
            self.force_login(user)
        return self.query(self.QUERY, variables=variables or {})

    def test_list_requires_authentication(self):
        # The global WhiteListMiddleware (helix/auth.py) blocks anonymous access
        # to any non-whitelisted root field, so the field resolves to null.
        content = self._post(None).json()
        self.assertIsNone(content["data"]["hulkBulkImports"])

    def test_list_visible_to_any_authenticated_user(self):
        # Reads are open to anyone authenticated — viewers see bulks created
        # by other users as well.
        resp = self._post(self.viewer)
        self.assertResponseNoErrors(resp)
        data = resp.json()["data"]["hulkBulkImports"]
        self.assertEqual(data["totalCount"], 3)
        returned_ids = {row["id"] for row in data["results"]}
        self.assertEqual(
            returned_ids,
            {str(self.bulk_a.id), str(self.bulk_b.id), str(self.bulk_c.id)},
        )

    def test_list_filters_by_status(self):
        resp = self._post(self.viewer, variables={"filters": {"statusList": ["COMPLETED"]}})
        self.assertResponseNoErrors(resp)
        data = resp.json()["data"]["hulkBulkImports"]
        self.assertEqual(data["totalCount"], 1)
        self.assertEqual(data["results"][0]["id"], str(self.bulk_b.id))

    def test_list_filters_by_created_by(self):
        resp = self._post(self.viewer, variables={"filters": {"createdByIds": [str(self.viewer.id)]}})
        self.assertResponseNoErrors(resp)
        data = resp.json()["data"]["hulkBulkImports"]
        self.assertEqual(data["totalCount"], 1)
        self.assertEqual(data["results"][0]["id"], str(self.bulk_c.id))

        # Multiple ids — union.
        resp = self._post(
            self.viewer,
            variables={"filters": {"createdByIds": [str(self.owner.id), str(self.viewer.id)]}},
        )
        self.assertResponseNoErrors(resp)
        data = resp.json()["data"]["hulkBulkImports"]
        self.assertEqual(data["totalCount"], 3)
