"""GPU metrics provider interface and built-in implementations.

A provider is a callable: () → dict
  Success: {"status": "available", "name": "...", "temperature_c": ..., ...}
  Failure: {"status": "unavailable", "error": "..."}

Built-in:
  file_provider(metrics_file, stale_seconds)  ← Phase 0 default
  (future) socket_provider(path)
  (future) sqlite_provider(db_path)
"""

import json
import os
import time


def file_provider(metrics_file: str, stale_seconds: int = 5):
    """Returns GPU metrics by reading a JSON file written by host-agent."""

    def _get() -> dict:
        try:
            mtime = os.path.getmtime(metrics_file)
            if time.time() - mtime > stale_seconds:
                return {"status": "unavailable", "error": "stale metrics"}
            with open(metrics_file) as f:
                return json.load(f)
        except FileNotFoundError:
            return {"status": "unavailable", "error": "host-agent not running"}
        except (json.JSONDecodeError, OSError) as e:
            return {"status": "unavailable", "error": str(e)}

    return _get
