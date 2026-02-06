from __future__ import annotations

import json
import pathlib
import typing
from contextlib import ExitStack

from pydantic import ValidationError

from pyhelix.api.api import HelixClient, helix_client_context

from .models import (
    HulkAttachmentImport,
    HulkBaseModel,
    HulkEntryImport,
    HulkEventImport,
    HulkFigureImport,
    HulkSourcePreviewImport,
)


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
        self._export_path_names: dict[typing.Type[HulkBaseModel], str] = {
            HulkAttachmentImport: "attachments.jsonl",
            HulkSourcePreviewImport: "source_previews.jsonl",
            HulkEntryImport: "entries.jsonl",
            HulkEventImport: "events.jsonl",
            HulkFigureImport: "figures.jsonl",
        }

        self._export_path_ref = {}
        self._export_error_path_ref = {}
        self._success_count = {import_type: 0 for import_type in self._export_path_names}
        self._error_count = {import_type: 0 for import_type in self._export_path_names}

    def __enter__(self):
        self._stack = ExitStack()

        # FIXME: Should we clear _success_count and _error_count on either __enter__ or __exit__?

        # Open all files when entering the context
        self._export_path_ref = {
            import_type: self._stack.enter_context((self.export_dir / path).open("w"))
            for import_type, path in self._export_path_names.items()
        }
        self._export_error_path_ref = {
            import_type: self._stack.enter_context((self.export_dir / f"errors_{path}").open("w"))
            for import_type, path in self._export_path_names.items()
        }

        self.helix_client.login()
        self._stack.enter_context(helix_client_context(self.helix_client))

        return self

    def __exit__(self, exc_type, exc, tb):
        # TODO: self.helix_client.logout()

        self._stack.__exit__(exc_type, exc, tb)

        self._export_path_ref.clear()
        self._export_error_path_ref.clear()

        # Return False to propagate exceptions (standard behavior)
        return False

    # TODO: Maybe rename this to get_debug_metadata?
    def debug_metadata(self):
        """
        For showing helpfull metadata from data preparation handler
        NOTE: The output might change in future
        """

        return {
            "count": {
                "success": {_type.__name__: count for _type, count in self._success_count.items()},
                "errors": {_type.__name__: count for _type, count in self._error_count.items()},
            },
            "files": {
                "success": [_path.name for _path in self._export_path_ref.values()],
                "errors": [_path.name for _path in self._export_error_path_ref.values()],
            },
        }

    def handle_import_object(self, obj: HulkBaseModel):
        _import_type = type(obj)
        self._export_path_ref[_import_type].write(obj.model_dump_json() + "\n")
        self._success_count[_import_type] += 1

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

    def send_to_helix(self):
        # TODO: Implement this
        raise NotImplementedError("Not yet implemented")
