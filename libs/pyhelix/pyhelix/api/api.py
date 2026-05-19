from __future__ import annotations

import contextvars
import enum
import json
import logging
import time
import typing
from contextlib import contextmanager
from pathlib import Path

import httpx

from pyhelix.api_types import HulkBulkImportState
from pyhelix.constants import HULK_BULK_IMPORT_STATUS

from .entities import (
    HelixCountry,
    HelixDisasterSubType,
    HelixFigureTag,
    HelixOrganization,
    HelixOtherSubType,
    HelixViolenceSubType,
)
from .queries import GraphqlQuery

logger = logging.getLogger(__name__)


# Short resource name → import_type enum value (matches helix's
# ``HulkBulkImportDataset.HULK_BULK_IMPORT_DATASET_IMPORT_TYPE`` enum). Iteration order matches the
# handler's dependency order: attachments → source_previews → entries →
# events → figures.
HULK_BULK_INPUT_FIELDS = (
    ("attachments", "ATTACHMENT"),
    ("source_previews", "SOURCE_PREVIEW"),
    ("entries", "ENTRY"),
    ("events", "EVENT"),
    ("figures", "FIGURE"),
)


HULK_BULK_TERMINAL_STATUSES = frozenset(
    {
        HULK_BULK_IMPORT_STATUS.COMPLETED,
        HULK_BULK_IMPORT_STATUS.FAILED,
        HULK_BULK_IMPORT_STATUS.SKIPPED,
    }
)


class HelixEndpoint:
    class BaseDomain(str, enum.Enum):
        PRODUCTION = "https://helix-tools-api.idmcdb.org"
        STAGING = "https://helix-tools-api-staging.idmcdb.org"

    def __init__(
        self,
        *,
        base_domain: BaseDomain | str,
        email: str,
        password: str,
    ):
        # TODO: Parse base_domain, strip path
        self.base_domain = base_domain.strip("/")
        self.email = email
        self.password = password
        if not (self.base_domain.startswith("https://") or self.base_domain.startswith("http://")):
            raise Exception(f"Invalid base domain: {self.base_domain}")

    @property
    def graphql(self) -> str:
        return f"{self.base_domain}/graphql"


class HelixClient:
    def __init__(self, endpoint: HelixEndpoint):
        self.endpoint = endpoint

        # TODO: Close this properly? Also logout?
        self._client = httpx.Client()

    def grequest(self, _json: dict):
        return self._client.post(
            self.endpoint.graphql,
            json=_json,
        )

    def me(self):
        return self.grequest(GraphqlQuery.me)

    def login(self):
        logger.info("Trying to login into helix server")
        try:
            resp = self.grequest(
                GraphqlQuery.login(
                    self.endpoint.email,
                    self.endpoint.password,
                ),
            )
            resp.raise_for_status()
        except Exception as e:
            raise Exception("Failed to authenticate") from e
        if not resp.json()["data"]["login"]["ok"]:
            raise Exception("Failed to authenticate")
        # TODO: Re-check validation here
        return resp

    # ------------------------------------------------------------------
    # Hulk bulk import — push JSONL via the triggerHulkBulkImport mutation
    # ------------------------------------------------------------------
    def trigger_hulk_bulk_import(
        self,
        jsonl_paths: typing.Mapping[str, typing.Union[str, Path]],
    ) -> str:
        """
        Trigger a HulkBulkImport with the given JSONL files. Returns the new
        ``HulkBulkImport.id``.

        ``jsonl_paths`` keys are short resource names (``"attachments"``,
        ``"source_previews"``, ``"entries"``, ``"events"``, ``"figures"``);
        values are filesystem paths to the JSONL files. Resources omitted from
        the mapping (or set to ``None``) are not uploaded — helix's serializer
        requires at least one.

        Sends a graphene-file-upload multipart request with a ``datasets``
        list, one entry per resource type::

            variables.data.datasets = [
                {importType: "ATTACHMENT", importFile: null},
                {importType: "ENTRY",      importFile: null},
                ...
            ]
            map = {
                "f0": ["variables.data.datasets.0.importFile"],
                "f1": ["variables.data.datasets.1.importFile"],
                ...
            }
        """
        present: list[tuple[str, str, Path]] = []
        for short, import_type in HULK_BULK_INPUT_FIELDS:
            path = jsonl_paths.get(short)
            if not path:
                continue
            p = Path(path)
            if not p.exists():
                raise FileNotFoundError(f"{short} JSONL missing: {p}")
            present.append((short, import_type, p))
        if not present:
            raise ValueError("trigger_hulk_bulk_import: at least one JSONL path is required")

        datasets = [{"importType": import_type, "importFile": None} for _, import_type, _ in present]
        operations = {
            "operationName": "pyhelixTriggerHulkBulkImport",
            "query": GraphqlQuery.trigger_hulk_bulk_import_query,
            "variables": {"data": {"datasets": datasets}},
        }
        # graphene-file-upload allows nested-index paths in the multipart map.
        file_map = {f"f{i}": [f"variables.data.datasets.{i}.importFile"] for i in range(len(present))}

        fhs = []
        try:
            files: dict = {}
            for i, (_, _, p) in enumerate(present):
                fh = p.open("rb")
                fhs.append(fh)
                files[f"f{i}"] = (p.name, fh, "application/x-jsonlines")
            resp = self._client.post(
                self.endpoint.graphql,
                data={
                    "operations": json.dumps(operations),
                    "map": json.dumps(file_map),
                },
                files=files,
                timeout=None,
            )
        finally:
            for fh in fhs:
                fh.close()
        if resp.status_code >= 400:
            # Surface the body so multipart/parse failures are debuggable.
            raise RuntimeError(f"triggerHulkBulkImport HTTP {resp.status_code}: {resp.text[:500]!r}")
        body = resp.json()
        if body.get("errors"):
            raise RuntimeError(f"triggerHulkBulkImport graphql errors: {body['errors']}")
        result = body["data"]["triggerHulkBulkImport"]
        if not result.get("ok"):
            raise RuntimeError(f"triggerHulkBulkImport rejected: {result.get('errors')}")
        return result["result"]["id"]

    def get_hulk_bulk_import(self, id: str) -> HulkBulkImportState:
        """Fetch the current state of a HulkBulkImport (status + counts + file URLs)."""
        resp = self.grequest(GraphqlQuery.hulk_bulk_import(id))
        resp.raise_for_status()
        body = resp.json()
        if body.get("errors"):
            raise RuntimeError(f"hulkBulkImport graphql errors: {body['errors']}")
        return HulkBulkImportState.model_validate(body["data"]["hulkBulkImport"])

    def wait_for_hulk_bulk_import(
        self,
        id: str,
        *,
        timeout: float = 3600.0,
        poll_interval: float = 5.0,
        progress_cb: typing.Optional[typing.Callable[[HulkBulkImportState], None]] = None,
    ) -> HulkBulkImportState:
        """
        Poll ``hulkBulkImport(id)`` until status is COMPLETED / FAILED /
        SKIPPED. Returns the final state. Raises ``TimeoutError`` if no
        terminal state is reached within ``timeout`` seconds.
        """
        deadline = time.monotonic() + timeout
        while True:
            state = self.get_hulk_bulk_import(id)
            if progress_cb is not None:
                progress_cb(state)
            if state.status in HULK_BULK_TERMINAL_STATUSES:
                return state
            if time.monotonic() > deadline:
                raise TimeoutError(f"HulkBulkImport {id} stuck at status={state.status.name}")
            time.sleep(poll_interval)

    @property
    def organization_manager(self) -> HelixOrganization:
        manager = getattr(self, "_organization_manager", None)
        if not manager:
            manager = self._organization_manager = HelixOrganization(self)
        return manager

    @property
    def country_manager(self) -> HelixCountry:
        manager = getattr(self, "_country_manager", None)
        if not manager:
            manager = self._country_manager = HelixCountry(self)
        return manager

    @property
    def violence_sub_type_manager(self) -> HelixViolenceSubType:
        manager = getattr(self, "_violence_sub_type_manager", None)
        if not manager:
            manager = self._violence_sub_type_manager = HelixViolenceSubType(self)
        return manager

    @property
    def disaster_sub_type_manager(self) -> HelixDisasterSubType:
        manager = getattr(self, "_disaster_sub_type_manager", None)
        if not manager:
            manager = self._disaster_sub_type_manager = HelixDisasterSubType(self)
        return manager

    @property
    def other_sub_type_manager(self) -> HelixOtherSubType:
        manager = getattr(self, "_other_sub_type_manager", None)
        if not manager:
            manager = self._other_sub_type_manager = HelixOtherSubType(self)
        return manager

    @property
    def figure_tag_manager(self) -> HelixFigureTag:
        manager = getattr(self, "_figure_tag_manager", None)
        if not manager:
            manager = self._figure_tag_manager = HelixFigureTag(self)
        return manager


# https://docs.python.org/3/library/contextvars.html
current_context: contextvars.ContextVar[HelixClient] = contextvars.ContextVar("helix_client_current_context")


# TODO: Use HelixClient as context manager?
def get_active_helix_client():
    ctx = typing.cast("HelixClient | None", current_context.get(None))
    if ctx is None:
        raise RuntimeError("HelixClient not set!")
    return ctx


@contextmanager
def helix_client_context(client: HelixClient):
    _client = current_context.set(client)
    try:
        yield
    finally:
        current_context.reset(_client)
