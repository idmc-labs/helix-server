from __future__ import annotations

import dataclasses
import json
import logging
import pathlib
import typing
from contextlib import ExitStack

import httpx
from pydantic import ValidationError

from pyhelix.api.api import HULK_BULK_INPUT_FIELDS, HelixClient, helix_client_context
from pyhelix.api_types import HulkBulkImportState

from .models import (
    HulkAttachmentImport,
    HulkBaseModel,
    HulkEntryImport,
    HulkEventImport,
    HulkFigureImport,
    HulkSourcePreviewImport,
)

logger = logging.getLogger(__name__)


# Maps each HulkBaseModel subclass to the short resource name expected by
# ``HelixClient.trigger_hulk_bulk_import`` (matches ``HULK_BULK_INPUT_FIELDS``).
_IMPORT_MODEL_TO_SHORT: typing.Dict[typing.Type[HulkBaseModel], str] = {
    HulkAttachmentImport: "attachments",
    HulkSourcePreviewImport: "source_previews",
    HulkEntryImport: "entries",
    HulkEventImport: "events",
    HulkFigureImport: "figures",
}


class DuplicateUuidError(RuntimeError):
    """Raised by :py:meth:`HulkDataHandler.send_to_helix` when a dataset repeats a uuid."""


# Written into ``export_dir`` alongside the per-resource JSONL, one line per
# repeat. The uuids themselves stay out of the log and the exception message:
# a data-prep bug that repeats a uuid usually repeats thousands of them, and a
# terminal is a poor place to read that list.
DUPLICATE_UUID_REPORT_NAME = "duplicate_uuids.jsonl"


@dataclasses.dataclass
class HulkBulkImportRun:
    """
    Handle to a triggered HulkBulkImport. Returned by
    :py:meth:`HulkDataHandler.send_to_helix`.

    Wraps the ``bulk_id`` and the originating :class:`HelixClient` so callers
    can poll status, wait for terminal state, and pull success/failure/skip
    artifacts without re-passing the client around.
    """

    helix_client: HelixClient
    bulk_id: str

    def get_state(self) -> HulkBulkImportState:
        """Return the current ``hulkBulkImport(id)`` payload."""
        return self.helix_client.get_hulk_bulk_import(self.bulk_id)

    def wait(
        self,
        *,
        timeout: float = 3600.0,
        poll_interval: float = 5.0,
        progress_cb: typing.Optional[typing.Callable[[HulkBulkImportState], None]] = None,
    ) -> HulkBulkImportState:
        """
        Block until the import reaches a terminal status (COMPLETED / FAILED /
        SKIPPED) and return the final state. ``progress_cb`` is invoked on
        every poll with the latest state.
        """
        return self.helix_client.wait_for_hulk_bulk_import(
            self.bulk_id,
            timeout=timeout,
            poll_interval=poll_interval,
            progress_cb=progress_cb,
        )

    def download_artifacts(self, out_dir: pathlib.Path) -> typing.Dict[str, typing.Dict[str, typing.Optional[pathlib.Path]]]:
        """
        Download ``success_<resource>.jsonl``, ``failure_<resource>.jsonl`` and
        ``skip_<resource>.jsonl`` for every dataset attached to this import
        into ``out_dir``.

        Returns ``{resource: {"success": path|None, "failure": path|None,
        "skip": path|None}}``. Missing URLs (e.g. no failures) are reported as
        ``None``.
        """
        state = self.get_state()
        out_dir.mkdir(parents=True, exist_ok=True)
        type_to_resource = {import_type: short for short, import_type in HULK_BULK_INPUT_FIELDS}
        artifacts: typing.Dict[str, typing.Dict[str, typing.Optional[pathlib.Path]]] = {}
        for ds in state.datasets or []:
            resource = type_to_resource.get(ds.import_type)
            if resource is None:
                continue
            entry: typing.Dict[str, typing.Optional[pathlib.Path]] = {}
            for kind, url in (("success", ds.success_file), ("failure", ds.failure_file), ("skip", ds.skip_file)):
                dst = out_dir / f"{kind}_{resource}.jsonl"
                entry[kind] = dst if (url and _download_to(url, dst)) else None
            artifacts[resource] = entry
        return artifacts


def open_jsonl_writer(path: pathlib.Path) -> typing.TextIO:
    """
    Open ``path`` for writing one JSON object per line.

    The rows carry source text in any script — Arabic, Devanagari, romanised
    transliterations with combining diacritics, U+2017 — so the encoding is
    pinned to UTF-8 rather than left to the platform locale. Windows' default
    is cp1252, which has no code point for those characters and would fail the
    write with ``UnicodeEncodeError``. ``newline="\\n"`` keeps the JSONL
    byte-identical across platforms, since helix reads the upload as bytes.
    """
    return path.open("w", encoding="utf-8", newline="\n")


def _download_to(url: str, dst: pathlib.Path) -> bool:
    """Fetch ``url`` and write to ``dst``. Returns True on success."""
    try:
        resp = httpx.get(url, follow_redirects=True, timeout=120)
        resp.raise_for_status()
    except Exception as e:
        logger.warning("download %s failed: %s", url, e)
        return False
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_bytes(resp.content)
    return True


class HulkDataHandler:
    def __init__(
        self,
        *,
        export_dir: pathlib.Path,
        helix_client: HelixClient,
    ):
        self.export_dir = export_dir
        self.helix_client = helix_client

        # TODO: Use HulkDataTypeEnum to add type check here to add names for each types
        self._export_path_names: typing.Dict[typing.Type[HulkBaseModel], str] = {
            HulkAttachmentImport: "attachments.jsonl",
            HulkSourcePreviewImport: "source_previews.jsonl",
            HulkEntryImport: "entries.jsonl",
            HulkEventImport: "events.jsonl",
            HulkFigureImport: "figures.jsonl",
        }

        self._export_path_ref: typing.Dict[typing.Type[HulkBaseModel], typing.TextIO] = {}
        self._export_error_path_ref: typing.Dict[typing.Type[HulkBaseModel], typing.TextIO] = {}
        self._success_count = {import_type: 0 for import_type in self._export_path_names}
        self._error_count = {import_type: 0 for import_type in self._export_path_names}
        # Uuids seen per dataset, held as ``UUID.int`` — the smallest object a uuid
        # already carries, so nothing extra is allocated per row. Scoped to each
        # dataset: the same uuid across two datasets (eg. an attachment and the entry
        # pointing at it) is not a duplicate.
        self._seen_uuids: typing.Dict[typing.Type[HulkBaseModel], typing.Set[int]] = {
            import_type: set() for import_type in self._export_path_names
        }
        # Repeat rows per dataset — the count only, since the uuids themselves go
        # straight to ``DUPLICATE_UUID_REPORT_NAME`` as they are seen.
        self._duplicate_uuid_count: typing.Dict[typing.Type[HulkBaseModel], int] = {
            import_type: 0 for import_type in self._export_path_names
        }
        self._duplicate_uuid_ref: typing.Optional[typing.IO] = None

    def __enter__(self):
        self._stack = ExitStack()

        self.export_dir.mkdir(parents=True, exist_ok=True)

        # Open all files when entering the context
        self._export_path_ref = {
            import_type: self._stack.enter_context(open_jsonl_writer(self.export_dir / path))
            for import_type, path in self._export_path_names.items()
        }
        self._export_error_path_ref = {
            import_type: self._stack.enter_context(open_jsonl_writer(self.export_dir / f"errors_{path}"))
            for import_type, path in self._export_path_names.items()
        }
        self._duplicate_uuid_ref = self._stack.enter_context(open_jsonl_writer(self.duplicate_uuid_report_path))

        # Bind the client so model code reached via get_active_helix_client()
        # resolves to this client for the duration of the block. Login and
        # client lifetime are the caller's responsibility.
        self._stack.enter_context(helix_client_context(self.helix_client))

        return self

    def __exit__(self, exc_type, exc, tb):
        self._stack.__exit__(exc_type, exc, tb)

        self._export_path_ref.clear()
        self._export_error_path_ref.clear()
        self._duplicate_uuid_ref = None

        # Return False to propagate exceptions (standard behavior)
        return False

    @property
    def duplicate_uuid_report_path(self) -> pathlib.Path:
        """Where repeated uuids are listed, next to the per-resource JSONL."""
        return self.export_dir / DUPLICATE_UUID_REPORT_NAME

    # TODO: Maybe rename this to get_debug_metadata?
    def debug_metadata(self):
        """
        For showing helpfull metadata from data preparation handler

        ``count["duplicates"]`` is the number of repeat rows per import type —
        rows whose uuid had already been written into the same dataset. The
        uuids themselves are in ``files["duplicates"]``; import types without a
        duplicate are left out of the count.

        NOTE: The output might change in future
        """

        return {
            "count": {
                "success": {_type.__name__: count for _type, count in self._success_count.items()},
                "errors": {_type.__name__: count for _type, count in self._error_count.items()},
                "duplicates": self._duplicate_uuid_counts(),
            },
            "files": {
                "success": [self._export_path_names[_type] for _type in self._export_path_names],
                "errors": [f"errors_{self._export_path_names[_type]}" for _type in self._export_path_names],
                "duplicates": DUPLICATE_UUID_REPORT_NAME,
            },
        }

    def _duplicate_uuid_counts(self) -> typing.Dict[str, int]:
        """Repeat rows per import type, keeping only the types that have any."""
        return {_type.__name__: count for _type, count in self._duplicate_uuid_count.items() if count}

    def handle_import_object(self, obj: HulkBaseModel):
        _import_type = type(obj)
        self._export_path_ref[_import_type].write(obj.model_dump_json() + "\n")
        self._success_count[_import_type] += 1

        seen = self._seen_uuids[_import_type]
        _uuid_int = obj.uuid.int
        if _uuid_int in seen:
            self._duplicate_uuid_count[_import_type] += 1
            if self._duplicate_uuid_ref is not None:
                self._duplicate_uuid_ref.write(
                    json.dumps({"import_type": _import_type.__name__, "uuid": str(obj.uuid)}) + "\n"
                )
        else:
            seen.add(_uuid_int)

    def handle_import_error(self, import_model: typing.Type[HulkBaseModel], exception: ValidationError):
        self._export_error_path_ref[import_model].write(exception.json() + "\n")
        self._error_count[import_model] += 1

    def handle_import_error_raw(self, import_model: typing.Type[HulkBaseModel], errors: dict):
        self._export_error_path_ref[import_model].write(
            json.dumps(
                {
                    "raw": errors,
                }
            )
            + "\n"
        )
        self._error_count[import_model] += 1

    def send_to_helix(self) -> HulkBulkImportRun:
        """
        Upload the JSONL files produced by this handler to helix via the
        ``triggerHulkBulkImport`` mutation and return a :class:`HulkBulkImportRun`
        the caller can poll for status / pull artifacts.

        A dataset repeating a uuid would create conflicting rows in helix, so
        the upload is refused with :class:`DuplicateUuidError` before anything
        is sent. The error carries a per-import-type repeat count and the path
        to ``DUPLICATE_UUID_REPORT_NAME``, which lists the offending uuids.

        Resources whose JSONL is empty (or missing) are skipped — helix's
        serializer requires at least one non-empty dataset, otherwise this
        method raises ``RuntimeError``.

        Safe to call inside or outside the context manager. Inside the block
        writers are still open in ``"w"`` mode — they're flushed here so the
        multipart upload's separate ``"rb"`` fd sees the tail of the buffer.
        After ``__exit__`` (or skip-generate) the writer dict is empty and the
        flush loop is a no-op; the JSONL on disk is already complete.
        """
        duplicates = self._duplicate_uuid_counts()
        if duplicates:
            # Called inside the context the writer is still open in ``"w"`` mode,
            # so flush before naming the file the caller is about to read.
            if self._duplicate_uuid_ref is not None:
                self._duplicate_uuid_ref.flush()
            summary = ", ".join(f"{type_name}: {count}" for type_name, count in sorted(duplicates.items()))
            raise DuplicateUuidError(
                f"send_to_helix: duplicate uuids found, nothing uploaded — repeat rows by import type "
                f"({summary}); uuids listed in {self.duplicate_uuid_report_path}"
            )

        for fh in self._export_path_ref.values():
            fh.flush()

        paths: typing.Dict[str, pathlib.Path] = {}
        for import_model, filename in self._export_path_names.items():
            short = _IMPORT_MODEL_TO_SHORT[import_model]
            path = self.export_dir / filename
            if path.exists() and path.stat().st_size > 0:
                paths[short] = path

        if not paths:
            raise RuntimeError(f"send_to_helix: no non-empty JSONL files in {self.export_dir}; nothing to upload.")

        logger.info("Uploading %d JSONL files to helix: %s", len(paths), sorted(paths))
        bulk_id = self.helix_client.trigger_hulk_bulk_import(paths)
        logger.info("Triggered HulkBulkImport id=%s", bulk_id)
        return HulkBulkImportRun(helix_client=self.helix_client, bulk_id=bulk_id)
