"""Health check: reports services status."""

import time
import logging
from urllib.request import urlopen
from urllib.error import URLError

from config import config

logger = logging.getLogger("m-acs.health")
START_TIME = time.time()


def get_health() -> dict:
    ollama = "running"
    try:
        with urlopen(f"{config.OLLAMA_URL}/", timeout=5) as resp:
            if resp.status != 200:
                ollama = "unreachable"
    except (URLError, OSError) as e:
        ollama = "unreachable"
        logger.warning("ollama health: %s", e)

    return {
        "status": "ok",
        "uptime_seconds": int(time.time() - START_TIME),
        "services": {
            "ollama": ollama,
            "control_plane": "running",
        },
        "version": "0.1.0",
    }
