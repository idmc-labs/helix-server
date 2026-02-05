import ast
import json
from datetime import datetime

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage


def persist(
    query_explanation: str,
    app_module: str,
) -> None:
    root = ast.literal_eval(query_explanation)[0]

    context = {
        "timestamp": datetime.utcnow().isoformat(),
        "query_tag": app_module,
        "planning_time_ms": root.get("Planning Time"),
        "execution_time_ms": root.get("Execution Time"),
    }

    rows: list[dict] = []

    def walk_plan(node: dict) -> None:
        rows.append(
            {
                "timestamp": context["timestamp"],
                "query_tag": context["query_tag"],
                "node_type": node.get("Node Type"),
                "relation": node.get("Relation Name"),
                "index": node.get("Index Name"),
                "actual_rows": node.get("Actual Rows"),
                "actual_time_ms": node.get("Actual Total Time"),
                "loops": node.get("Actual Loops"),
                "planning_time_ms": context["planning_time_ms"],
                "execution_time_ms": context["execution_time_ms"],
                "shared_hit_blocks": node.get("Shared Hit Blocks", 0),
                "shared_read_blocks": node.get("Shared Read Blocks", 0),
                "shared_dirtied_blocks": node.get("Shared Dirtied Blocks", 0),
                "shared_written_blocks": node.get("Shared Written Blocks", 0),
            }
        )

        for child in node.get("Plans", []):
            walk_plan(child)

    walk_plan(root["Plan"])

    json_string = json.dumps(rows, indent=4)
    json_bytes = json_string.encode("utf-8")

    default_storage.save(f"{app_module}.json", ContentFile(json_bytes))
