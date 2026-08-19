from django.test import SimpleTestCase

from apps.users.enums import USER_ROLE
from utils.factories import ExtractionQueryFactory, TagFactory
from utils.tests import HelixGraphQLTestCase, create_user_with_role

NONEXISTENT_ID = "999999"

PAYLOAD_FIELDS = "ok errors"


class TestMutationErrorBranches(HelixGraphQLTestCase):
    """Mutations report failures through a hand-written errors payload
    (nonFieldErrors for missing instances, field-keyed entries for serializer
    validation) rather than GraphQL errors. Exercise those branches across
    apps; the happy paths are covered by each app's own tests."""

    def setUp(self):
        self.user = create_user_with_role(USER_ROLE.ADMIN.name)
        self.force_login(self.user)

    def _mutation_payload(self, body):
        response = self.query("mutation { %s }" % body)
        self.assertResponseNoErrors(response)
        (payload,) = response.json()["data"].values()
        return payload

    def _assert_error(self, body, field="nonFieldErrors", message="does not exist"):
        payload = self._mutation_payload(body)
        self.assertFalse(payload["ok"], payload)
        self.assertTrue(payload["errors"], payload)
        error_fields = [error["field"] for error in payload["errors"]]
        self.assertIn(field, error_fields, payload)
        if message:
            self.assertIn(message, payload["errors"][0]["messages"].lower(), payload)

    def test_delete_mutations_with_nonexistent_id(self):
        for name in (
            "deleteActor",
            "deleteContextOfViolence",
            "deleteFigureTag",
            "deleteContact",
            "deleteCommunication",
            "deleteResource",
            "deleteResourceGroup",
            "deleteExtraction",
            "deleteOrganizationKind",
            "deletePortfolio",
            "deleteReportComment",
        ):
            with self.subTest(mutation=name):
                self._assert_error(f'{name}(id: "{NONEXISTENT_ID}") {{ {PAYLOAD_FIELDS} }}')

    def test_update_mutations_with_nonexistent_id(self):
        cases = [
            ("updateActor", "does not exist"),
            ("updateContextOfViolence", "does not exist"),
            ("updateFigureTag", "does not exist"),
            ("updateContact", "does not exist"),
            ("updateCommunication", "does not exist"),
            ("updateResource", "does not exist"),
            ("updateResourceGroup", "does not exist"),
            ("updateExtraction", "does not exist"),
            ("updateOrganizationKind", "does not exist"),
            ("updateUser", "not found"),
            ("updateClient", "does not exist"),
        ]
        for name, message in cases:
            with self.subTest(mutation=name):
                self._assert_error(
                    f'{name}(data: {{id: "{NONEXISTENT_ID}"}}) {{ {PAYLOAD_FIELDS} }}',
                    message=message,
                )

    def test_update_regional_coordinator_portfolio_without_portfolio(self):
        self._assert_error(
            'updateRegionalCoordinatorPortfolio(data: {user: "%s", monitoringSubRegion: "%s"}) { %s }'
            % (self.user.id, NONEXISTENT_ID, PAYLOAD_FIELDS),
        )

    # NOTE: CreateSourcePreview's "Preview does not exist." branch is
    # unreachable through the API: SourcePreviewInputType exposes no `id`.

    def test_create_mutations_with_invalid_data(self):
        cases = [
            ("createActor", '{name: "Actor", country: "%s"}' % NONEXISTENT_ID, "country"),
            ("createContextOfViolence", '{name: ""}', "name"),
            ("createFigureTag", '{name: ""}', "name"),
            ("createOrganizationKind", '{name: ""}', "name"),
            ("createResourceGroup", '{name: ""}', "name"),
            (
                "createResource",
                '{name: "Resource", url: "https://example.com", countries: ["%s"]}' % NONEXISTENT_ID,
                "countries",
            ),
            ("createExtraction", '{name: ""}', "name"),
        ]
        for name, data, field in cases:
            with self.subTest(mutation=name):
                self._assert_error(f"{name}(data: {data}) {{ {PAYLOAD_FIELDS} }}", field=field, message=None)

    def test_update_mutations_with_invalid_data(self):
        tag = TagFactory.create()
        extraction = ExtractionQueryFactory.create(created_by=self.user)
        cases = [
            ("updateFigureTag", tag.id),
            ("updateExtraction", extraction.id),
        ]
        for name, instance_id in cases:
            with self.subTest(mutation=name):
                self._assert_error(
                    f'{name}(data: {{id: "{instance_id}", name: ""}}) {{ {PAYLOAD_FIELDS} }}',
                    field="name",
                    message=None,
                )


class TestMutationsReturnTheirOwnPayload(SimpleTestCase):
    """Every branch of a mutation must construct its OWN payload class.

    Nothing above can see this: graphene resolves payload fields with `dict_or_attr_resolver`,
    so a sibling class carrying the same attribute names is indistinguishable over the wire.
    Covers every `apps/**/mutations.py` plus `utils/mutation.py`, which holds a base mutation.
    """

    def test_no_mutation_returns_a_foreign_payload_class(self):
        import ast
        import pathlib

        root = pathlib.Path(__file__).resolve().parents[3]
        paths = sorted(root.glob("apps/**/mutations.py")) + [root / "utils" / "mutation.py"]
        # A relative glob would resolve against the caller's directory and quietly scan nothing,
        # which is the one way this assertion could pass without checking anything.
        self.assertGreater(len(paths), 15, f"the walk scanned {len(paths)} files")

        offenders = []
        for path in paths:
            tree = ast.parse(path.read_text())
            for node in ast.walk(tree):
                if not isinstance(node, ast.ClassDef):
                    continue
                mutate = next((m for m in node.body if isinstance(m, ast.FunctionDef) and m.name == "mutate"), None)
                if mutate is None:
                    continue
                # Only `mutate`, and not a class nested inside it: a sibling helper returning any
                # capitalised call, or an inner class returning its own payload, is not an offender.
                nested = {id(inner) for c in ast.walk(mutate) if isinstance(c, ast.ClassDef) for inner in ast.walk(c)}
                for sub in ast.walk(mutate):
                    if id(sub) in nested or not (isinstance(sub, ast.Return) and isinstance(sub.value, ast.Call)):
                        continue
                    called = getattr(sub.value.func, "id", None)
                    if called and called[0].isupper() and called != node.name:
                        offenders.append(f"{path.name}:{sub.lineno} {node.name} returns {called}")
        self.assertEqual(offenders, [], "these branches return another class's payload")
