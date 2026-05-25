"""Model operations: list, delete."""

import json
import logging
from urllib.request import urlopen, Request
from urllib.error import URLError

from config import config
from services.exceptions import ServiceUnavailable

logger = logging.getLogger("m-acs.models")


def get_models() -> dict:
    try:
        with urlopen(f"{config.OLLAMA_URL}/api/tags", timeout=10) as resp:
            return json.loads(resp.read())
    except URLError as e:
        logger.warning("ollama unreachable: %s", e.reason)
        raise ServiceUnavailable(f"ollama unavailable: {e.reason}")
    except OSError as e:
        logger.warning("models network error: %s", e)
        raise ServiceUnavailable(f"network error: {e}")


def delete_model(name: str):
    try:
        req = Request(
            f"{config.OLLAMA_URL}/api/delete",
            data=json.dumps({"name": name}).encode(),
            headers={"Content-Type": "application/json"},
            method="DELETE",
        )
        with urlopen(req, timeout=30) as resp:
            if resp.status not in (200, 204):
                raise ServiceUnavailable(f"ollama returned {resp.status}")
    except URLError as e:
        raise ServiceUnavailable(f"delete failed: {e.reason}")
