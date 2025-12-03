import time
import functools
import json
from datetime import datetime, timezone
from pathlib import Path
import traceback

def timeprofiler(
    cpu_time=False,
    json_log_file="profiler.jsonl",
):
    """
    A execution time profiler that logs output to JSON Lines for visualization.
    Args:
        logger: Logger instance to use.
        level: Logging level.
        log_args: Whether to log function arguments.
        cpu_time: If True, uses CPU time instead of wall time.
        json_log_file: Path to JSONL file storing timing logs.
    """
    json_log_path = Path(json_log_file)
    json_log_path.parent.mkdir(parents=True, exist_ok=True)

    timer = time.process_time if cpu_time else time.perf_counter

    def decorator(func):
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            start = timer()
            exc_info = ""
            end = 0
            row_count = 0
            try:
                end = timer()
                results = func(*args, **kwargs)
                row_count = len(results['data'])
                return results
            except Exception as e:
                end = timer()
                exc_info = traceback.format_exc()
                raise
            finally:
                duration = end - start
                kwargs.update(row_count=row_count)
                _write_json_log(func, duration, kwargs, json_log_path, exc_info)

        return sync_wrapper

    return decorator

def _write_json_log(func, duration, kwargs, file_path: Path, exc_info: str):
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "func": func.__qualname__,
        "duration_ms": round(duration * 1000, 4),
    }
    record = {**record, **kwargs}
    if exc_info:
        record["exception"] = exc_info

    with file_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")
