#!/usr/bin/env python3
"""GPU metrics collector. Runs on host (systemd), writes to file.

Data flow: nvidia-smi → JSON file → control-plane reads via bind mount.
Silent on success, logs WARNING on failure.
"""

import subprocess
import json
import time
import os
import sys
import logging
import signal

METRICS_FILE = sys.argv[1] if len(sys.argv) > 1 else "/opt/m-acs-1/data/gpu.json"
POLL_INTERVAL = int(os.getenv("COLLECTOR_POLL_INTERVAL", "2"))
NVIDIA_SMI = os.getenv("NVIDIA_SMI_BIN", "")

logging.basicConfig(level=logging.WARNING, format="collector: %(message)s")
logger = logging.getLogger("collector")

_running = True


def _find_nvidia_smi():
    """Locate nvidia-smi binary. WSL2 puts it in /usr/lib/wsl/lib/."""
    candidates = [
        NVIDIA_SMI,
        "/usr/lib/wsl/lib/nvidia-smi",
        "/usr/bin/nvidia-smi",
        "nvidia-smi",
    ]
    import shutil
    for c in filter(None, candidates):
        if shutil.which(c) or os.path.isfile(c):
            return c
    return "nvidia-smi"


def _stop(_signum, _frame):
    global _running
    _running = False


signal.signal(signal.SIGTERM, _stop)
signal.signal(signal.SIGINT, _stop)


def _int(v):
    try:
        return int(v)
    except Exception:
        return 0


def _flt(v):
    try:
        return float(v)
    except Exception:
        return 0.0


def collect():
    os.makedirs(os.path.dirname(METRICS_FILE), exist_ok=True)
    nvidia_smi = _find_nvidia_smi()

    # Initial delay: let GPU driver finish loading after boot
    time.sleep(5)

    while _running:
        try:
            r = subprocess.run(
                [
                    nvidia_smi,
                    "--query-gpu=name,temperature.gpu,memory.used,memory.total,"
                    "utilization.gpu,power.draw,power.limit,driver_version",
                    "--format=csv,noheader,nounits",
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if r.returncode != 0 or not r.stdout.strip():
                raise RuntimeError(f"nvidia-smi rc={r.returncode} stderr={r.stderr.strip()}")

            f = [x.strip() for x in r.stdout.strip().split(",")]
            data = {
                "status": "available",
                "name": f[0],
                "temperature_c": _int(f[1]),
                "memory_used_mb": _int(f[2]),
                "memory_total_mb": _int(f[3]),
                "utilization_pct": _int(f[4]),
                "power_draw_w": _flt(f[5]),
                "power_limit_w": _flt(f[6]),
                "driver_version": f[7],
            }
        except Exception as e:
            data = {"status": "unavailable", "error": str(e)}
            logger.warning("collect failed: %s", e)

        # Atomic write
        tmp = METRICS_FILE + ".tmp"
        try:
            with open(tmp, "w") as f:
                json.dump(data, f)
            os.replace(tmp, METRICS_FILE)
        except OSError as e:
            logger.warning("write failed: %s", e)

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    collect()
