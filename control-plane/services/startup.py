"""Startup integrity checks. Runs once on boot, caches results."""

import os
import time
import logging
from urllib.request import urlopen
from urllib.error import URLError

from config import config

logger = logging.getLogger("m-acs.startup")

_startup_checks = None
_startup_time = None


def run_startup_checks() -> list[dict]:
    """Run all startup integrity checks. Returns list of check results."""
    checks = []
    all_ok = True

    # 1. Data directory writable
    data_dir = os.path.dirname(config.RAG_DB_PATH) or "/data"
    dir_writable = os.access(data_dir, os.W_OK) if os.path.exists(data_dir) else False
    dir_ok = os.path.exists(data_dir) and dir_writable
    checks.append({
        "name": "data_directory",
        "status": "ok" if dir_ok else "error",
        "detail": f"{data_dir} {'writable' if dir_ok else ('not found' if not os.path.exists(data_dir) else 'not writable')}",
        "recovery": "Ensure /data directory exists and is writable: mkdir -p /data && chmod 755 /data" if not dir_ok else "",
    })
    if not dir_ok:
        all_ok = False

    # 2. RAG DB presence
    db_exists = os.path.exists(config.RAG_DB_PATH)
    db_writable = os.access(config.RAG_DB_PATH, os.W_OK) if db_exists else dir_writable
    if db_exists:
        db_size = os.path.getsize(config.RAG_DB_PATH)
        db_ok = db_writable
        checks.append({
            "name": "rag_database",
            "status": "ok" if db_ok else "error",
            "detail": f"{fmt_size(db_size)} {'writable' if db_ok else 'NOT WRITABLE'}",
            "recovery": "Check file permissions: chmod 644 " + config.RAG_DB_PATH if not db_ok else "",
        })
        if not db_ok:
            all_ok = False
    else:
        checks.append({"name": "rag_database", "status": "ok", "detail": "not created — will create on first upload", "recovery": ""})

    # 3. Ollama connectivity
    try:
        resp = urlopen(f"{config.OLLAMA_URL}/", timeout=10)
        ollama_ok = resp.status == 200
        checks.append({
            "name": "ollama_connectivity",
            "status": "ok" if ollama_ok else "error",
            "detail": "reachable" if ollama_ok else f"status {resp.status}",
            "recovery": "Ensure Ollama service is running: docker start ollama" if not ollama_ok else "",
        })
        if not ollama_ok:
            all_ok = False
    except (URLError, OSError) as e:
        checks.append({"name": "ollama_connectivity", "status": "error", "detail": str(e), "recovery": "Check Ollama URL in config or ensure Ollama container is running"})
        all_ok = False

    # 4. RAG embedding model
    try:
        import json
        req = urlopen(f"{config.OLLAMA_URL}/api/tags", timeout=15)
        if req.status == 200:
            models = json.loads(req.read()).get("models", [])
            model_names = [m["name"] for m in models]
            embed_avail = config.RAG_EMBED_MODEL in model_names
            checks.append({
                "name": "rag_embedding_model",
                "status": "ok" if embed_avail else "warning",
                "detail": f"{config.RAG_EMBED_MODEL} {'installed' if embed_avail else 'not installed — will pull on demand'}",
                "recovery": f"Pull the model: ollama pull {config.RAG_EMBED_MODEL}" if not embed_avail else "",
            })
    except Exception as e:
        checks.append({"name": "rag_embedding_model", "status": "warning", "detail": f"could not check: {e}", "recovery": ""})

    # 5. GPU Monitor metrics file
    metrics_file = config.GPU_METRICS_FILE
    if os.path.exists(metrics_file):
        metrics_age = time.time() - os.path.getmtime(metrics_file)
        gpu_ok = metrics_age < 60
        checks.append({
            "name": "gpu_monitor",
            "status": "ok" if gpu_ok else "warning",
            "detail": f"last update {int(metrics_age)}s ago" if gpu_ok else f"stale ({int(metrics_age)}s old)",
            "recovery": "Check host-agent service: systemctl status m-acs-host-agent" if not gpu_ok else "",
        })
    else:
        checks.append({"name": "gpu_monitor", "status": "ok", "detail": "metrics file not yet created — host-agent may be starting", "recovery": ""})

    # 6. Storage pressure (available disk space)
    try:
        import shutil
        usage = shutil.disk_usage(data_dir)
        free_gb = usage.free / (1024 ** 3)
        pct = usage.used / usage.total * 100
        if free_gb < 0.5:
            storage_status = "error"
        elif free_gb < 2:
            storage_status = "warning"
        else:
            storage_status = "ok" if pct < 90 else "warning"
        checks.append({
            "name": "storage_pressure",
            "status": storage_status,
            "detail": f"{free_gb:.1f} GB free ({pct:.0f}% used)",
            "recovery": f"Free up disk space: remove unused models or backups" if storage_status != "ok" else "",
        })
        if storage_status == "error":
            all_ok = False
    except Exception:
        pass

    global _startup_checks, _startup_time
    _startup_checks = checks
    _startup_time = time.time()

    return checks


def get_startup_status() -> dict:
    """Get cached startup results, running checks if not yet done."""
    global _startup_checks, _startup_time
    if _startup_checks is None:
        run_startup_checks()
    return {
        "checks": _startup_checks or [],
        "all_ok": all(c["status"] == "ok" for c in (_startup_checks or [])),
        "startup_timestamp": _startup_time,
        "uptime_seconds": int(time.time() - (_startup_time or time.time())),
    }


def fmt_size(b: int) -> str:
    if b is None:
        return "N/A"
    if b > 1e9:
        return f"{b/1e9:.1f} GB"
    if b > 1e6:
        return f"{b/1e6:.1f} MB"
    if b > 1e3:
        return f"{b/1e3:.0f} KB"
    return f"{b} B"
