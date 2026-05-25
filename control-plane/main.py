import json as _json
import logging
import os

from fastapi import FastAPI, HTTPException, Request, UploadFile, File
from fastapi.responses import StreamingResponse, FileResponse
from starlette.background import BackgroundTask
from config import config
from services import gpu as gpu_svc
from services import models as model_svc
from services import health as health_svc
from services.exceptions import ServiceUnavailable

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("m-acs")

HERE = os.path.dirname(os.path.abspath(__file__))
STATIC = os.path.join(HERE, "static")

app = FastAPI(title="M-ACS-1 Control Plane")


@app.get("/health")
def live():
    return {"status": "ok"}


@app.get("/api/health")
def api_health():
    return health_svc.get_health()


@app.get("/api/gpu")
def gpu():
    try:
        data = gpu_svc.get_gpu_metrics()
        if data.get("status") == "unavailable":
            raise ServiceUnavailable(data.get("error", "gpu unavailable"))
        return data
    except ServiceUnavailable as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.exception("unexpected error in /api/gpu")
        raise HTTPException(status_code=500, detail={"error": str(e)})


@app.get("/api/models")
def models():
    try:
        return model_svc.get_models()
    except ServiceUnavailable as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.exception("unexpected error in /api/models")
        raise HTTPException(status_code=500, detail={"error": str(e)})


@app.post("/api/models/delete")
def delete_model(data: dict):
    name = data.get("name", "")
    if not name:
        raise HTTPException(status_code=400, detail="model name required")
    try:
        model_svc.delete_model(name)
        return {"status": "deleted", "name": name}
    except ServiceUnavailable as e:
        raise HTTPException(status_code=503, detail=str(e))


@app.post("/api/pull")
def pull_model(data: dict):
    """Pull a model. Normalizes Ollama NDJSON → SSE for browser."""
    from urllib.request import Request, urlopen

    def events():
        req = Request(
            f"{config.OLLAMA_URL}/api/pull",
            data=_json.dumps({"name": data["name"], "stream": True}).encode(),
            headers={"Content-Type": "application/json"},
        )
        try:
            with urlopen(req, timeout=300) as resp:
                for line in resp:
                    line = line.decode().strip()
                    if not line:
                        continue
                    try:
                        d = _json.loads(line)
                    except _json.JSONDecodeError:
                        continue
                    ev = {"type": "status", "message": d.get("status", "")}
                    if d.get("completed") is not None and d.get("total"):
                        ev["pct"] = round(d["completed"] / d["total"] * 100, 1)
                        ev["type"] = "progress"
                    yield f"data: {_json.dumps(ev)}\n\n"
                yield f"data: {_json.dumps({'type': 'done', 'message': 'complete'})}\n\n"
        except Exception as e:
            logger.warning("pull failed: %s", e)
            yield f"data: {_json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(events(), media_type="text/event-stream")


# ── Document RAG API ──
import tempfile
import os as _os

RAG_DB = config.RAG_DB_PATH


@app.post("/api/documents/upload")
async def upload_document(file: UploadFile = File(...)):
    """Upload a PDF for ingestion."""
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="仅支持 PDF 文件")

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    try:
        content = await file.read()
        tmp.write(content)
        tmp.close()

        from rag.store import ingest_file
        result = ingest_file(tmp.name, RAG_DB, config.OLLAMA_URL, filename=file.filename)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("ingestion failed")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        _os.unlink(tmp.name)


@app.get("/api/documents")
def list_documents():
    """List ingested documents."""
    from rag.store import list_files
    return {"files": list_files(RAG_DB)}


@app.delete("/api/documents/{doc_id}")
def delete_document(doc_id: int):
    """Delete a document and all its chunks."""
    from rag.store import delete_file
    delete_file(RAG_DB, doc_id)
    return {"status": "deleted"}


@app.get("/api/documents/{doc_id}/chunks")
def get_chunks(doc_id: int):
    """Get all chunks for a document (document outline)."""
    from rag.db import get_db
    db = get_db(RAG_DB)
    rows = db.execute(
        "SELECT id, content, page_num, chunk_index, tokens FROM chunks WHERE file_id = ? ORDER BY chunk_index",
        (doc_id,),
    ).fetchall()
    db.close()

    result = []
    for r in rows:
        section = extract_section(r["content"])
        result.append({
            "id": r["id"],
            "content": r["content"],
            "page": r["page_num"],
            "index": r["chunk_index"],
            "tokens": r["tokens"],
            "section": section,
        })
    return {"chunks": result, "total": len(result)}


@app.get("/api/documents/{doc_id}/chunks/{chunk_id}/context")
def get_chunk_context(doc_id: int, chunk_id: int):
    """Get a chunk with its neighboring chunks for context."""
    from rag.db import get_db
    db = get_db(RAG_DB)

    # Get current chunk
    current = db.execute(
        "SELECT id, content, page_num, chunk_index, tokens FROM chunks WHERE id = ? AND file_id = ?",
        (chunk_id, doc_id),
    ).fetchone()
    if not current:
        db.close()
        raise HTTPException(status_code=404, detail="chunk not found")

    # Get previous chunk
    prev_chunk = db.execute(
        "SELECT id, content, page_num, chunk_index FROM chunks WHERE file_id = ? AND chunk_index < ? ORDER BY chunk_index DESC LIMIT 1",
        (doc_id, current["chunk_index"]),
    ).fetchone()

    # Get next chunk
    next_chunk = db.execute(
        "SELECT id, content, page_num, chunk_index FROM chunks WHERE file_id = ? AND chunk_index > ? ORDER BY chunk_index ASC LIMIT 1",
        (doc_id, current["chunk_index"]),
    ).fetchone()

    db.close()

    def format_chunk(r):
        if not r:
            return None
        return {
            "id": r[0],
            "content": r[2],
            "page": r[3],
            "index": r[4],
        }

    return {
        "current": format_chunk(current),
        "prev": format_chunk(prev_chunk) if prev_chunk else None,
        "next": format_chunk(next_chunk) if next_chunk else None,
    }


def extract_section(content: str) -> str:
    """Extract section heading from chunk content."""
    import re
    for line in content.split("\n"):
        line = line.strip()
        if re.match(r'^(Article|Section|Chapter|Part|Clause|第[一二三四五六七八九十百千零\d]+[章节条])', line):
            return line[:60]
    return ""


@app.post("/api/documents/ask")
def ask_documents(data: dict):
    """Ask a question against ingested documents."""
    question = data.get("question", "").strip()
    if not question:
        raise HTTPException(status_code=400, detail="question is required")
    file_ids = data.get("file_ids")  # optional

    from rag.retriever import retrieve, format_context, group_by_file

    try:
        chunks = retrieve(RAG_DB, config.OLLAMA_URL, question, file_ids)
    except Exception as e:
        logger.exception("retrieval failed")
        raise HTTPException(status_code=500, detail=str(e))

    if not chunks:
        return {"answer": "未找到相关文档内容", "sources": [], "groups": []}

    context = format_context(chunks)
    prompt = (
        "你是一个专业文档分析助手。基于以下文档内容回答用户问题。\n"
        "如果文档中没有相关信息，请明确说'文档中未提及'，不要编造。\n"
        "回答时请引用具体的文件名称和页码。\n\n"
        f"文档内容：\n{context}\n\n"
        f"问题：{question}\n---"
    )

    # Call Ollama
    import httpx
    try:
        resp = httpx.post(
            f"{config.OLLAMA_URL}/api/chat",
            json={
                "model": data.get("model", "qwen2.5:0.5b"),
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
            },
            timeout=120,
        )
        resp.raise_for_status()
        answer = resp.json()["message"]["content"]
    except Exception as e:
        logger.exception("ollama chat failed")
        raise HTTPException(status_code=503, detail=f"AI Engine error: {e}")

    groups = group_by_file(chunks)
    return {"answer": answer, "sources": groups}


# Proxy remaining /api/* and /v1/* to Ollama
@app.api_route("/api/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])
@app.api_route("/v1/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])
async def api_ollama_proxy(path: str, request: Request):
    """Forward unhandled API paths to Ollama."""
    prefix = "/v1/" if request.url.path.startswith("/v1/") else "/api/"
    url = f"{config.OLLAMA_URL}{prefix}{path}"
    body = await request.body()

    exclude = {"host", "content-length", "connection", "transfer-encoding"}
    headers = {k: v for k, v in request.headers.items() if k.lower() not in exclude}

    import httpx
    client = httpx.AsyncClient(timeout=300)
    try:
        req = client.build_request(request.method, url, headers=headers, content=body)
        resp = await client.send(req, stream=True)

        out_headers = {k: v for k, v in resp.headers.items()
                       if k.lower() not in exclude}

        return StreamingResponse(
            resp.aiter_bytes(),
            status_code=resp.status_code,
            headers=out_headers,
            background=BackgroundTask(client.aclose),
        )
    except Exception:
        await client.aclose()
        raise


@app.get("/api/system/storage")
def system_storage():
    """Report storage usage."""
    def fmt_size(path):
        try:
            return os.path.getsize(path)
        except OSError:
            return None

    rag_size = fmt_size(RAG_DB)
    doc_count = 0
    pages_total = 0
    storage = {
        "rag_db_bytes": rag_size,
        "rag_db_path": RAG_DB,
        "documents": {"count": doc_count, "total_pages": pages_total},
    }
    try:
        from rag.db import get_db
        db = get_db(RAG_DB)
        doc_count = db.execute("SELECT COUNT(*) as c FROM files").fetchone()["c"]
        pages = db.execute("SELECT COALESCE(SUM(pages),0) as p FROM files").fetchone()["p"]
        db.close()
        storage["documents"]["count"] = doc_count
        storage["documents"]["total_pages"] = pages
    except Exception:
        pass

    # Model info from Ollama (proxy)
    import httpx
    try:
        resp = httpx.get(f"{config.OLLAMA_URL}/api/tags", timeout=10)
        if resp.status_code == 200:
            models = resp.json().get("models", [])
            storage["models"] = {
                "count": len(models),
                "total_size_bytes": sum(m.get("size", 0) for m in models),
            }
    except Exception:
        storage["models"] = {"count": None, "total_size_bytes": None}

    # Lifecycle state
    _has_data = False
    try:
        from rag.db import get_db as _gdb2
        _db3 = _gdb2(RAG_DB)
        _has_data = _db3.execute("SELECT COUNT(*) as c FROM files").fetchone()["c"] > 0
        _db3.close()
    except Exception:
        pass
    storage["lifecycle"] = "clean" if not _has_data else "active"

    return storage


@app.get("/api/system/diagnostics")
def system_diagnostics():
    """Health diagnostics: DB integrity, model check, storage."""
    import httpx
    results = {"checks": [], "healthy": True}

    # Check Ollama
    try:
        resp = httpx.get(f"{config.OLLAMA_URL}/api/tags", timeout=10)
        models = resp.json().get("models", []) if resp.status_code == 200 else []
        results["checks"].append({"name": "ollama", "status": "ok" if resp.status_code == 200 else "error", "detail": f"{len(models)} models" if resp.status_code == 200 else str(resp.status_code)})
    except Exception as e:
        results["checks"].append({"name": "ollama", "status": "error", "detail": str(e)})
        results["healthy"] = False

    # Check RAG DB integrity
    try:
        from rag.db import get_db
        db = get_db(RAG_DB)
        file_count = db.execute("SELECT COUNT(*) as c FROM files").fetchone()["c"]
        chunk_count = db.execute("SELECT COUNT(*) as c FROM chunks").fetchone()["c"]
        vec_count = db.execute("SELECT COUNT(*) as c FROM vec_chunks").fetchone()["c"]
        db.close()
        consistent = chunk_count == vec_count
        results["checks"].append({"name": "vector_db", "status": "ok" if consistent else "warning", "detail": f"{file_count} files, {chunk_count} chunks, {vec_count} vectors" + ("" if consistent else " (MISMATCH!)")})
        if not consistent:
            results["healthy"] = False
    except Exception as e:
        results["checks"].append({"name": "vector_db", "status": "error", "detail": str(e)})
        results["healthy"] = False

    # Check storage
    try:
        db_size = os.path.getsize(RAG_DB)
        results["checks"].append({"name": "storage", "status": "ok", "detail": fmt_size_human(db_size) if db_size else "0 B"})
    except Exception as e:
        results["checks"].append({"name": "storage", "status": "warning", "detail": str(e)})

    # Startup: DB exists and writable
    db_exists = os.path.exists(RAG_DB)
    db_writable = os.access(os.path.dirname(RAG_DB) or ".", os.W_OK) if db_exists else os.access(os.path.dirname(RAG_DB) or ".", os.W_OK)
    if not db_exists:
        results["checks"].append({"name": "database", "status": "ok", "detail": "not created yet — will be created on first upload"})
    elif not db_writable:
        results["checks"].append({"name": "database", "status": "error", "detail": "exists but NOT WRITABLE"})
        results["healthy"] = False
    else:
        results["checks"].append({"name": "database", "status": "ok", "detail": "exists and writable"})

    # Startup: RAG model available
    try:
        import httpx as _httpx2
        _resp = _httpx2.get(f"{config.OLLAMA_URL}/api/tags", timeout=10)
        if _resp.status_code == 200:
            _models = _resp.json().get("models", [])
            _rag_avail = config.RAG_EMBED_MODEL in [m["name"] for m in _models]
            results["checks"].append({"name": "rag_model", "status": "ok" if _rag_avail else "warning", "detail": (config.RAG_EMBED_MODEL + " installed") if _rag_avail else (config.RAG_EMBED_MODEL + " not installed — will pull on demand")})
    except Exception:
        pass

    # Lifecycle state
    _has_data = False
    try:
        from rag.db import get_db as _gdb
        _db2 = _gdb(RAG_DB)
        _has_data = _db2.execute("SELECT COUNT(*) as c FROM files").fetchone()["c"] > 0
        _db2.close()
    except Exception:
        pass
    results["lifecycle"] = "clean" if not _has_data else "active"
    results["version"] = "0.1.0"

    return results


@app.post("/api/system/reset")
def system_reset(data: dict):
    """Safe reset. Scope: session, docs, all."""
    scope = data.get("scope", "")
    if scope not in ("session", "docs", "all"):
        raise HTTPException(status_code=400, detail="scope must be 'session', 'docs', or 'all'")

    results = {"status": "ok", "scope": scope, "actions": []}

    if scope in ("docs", "all"):
        try:
            from rag.db import get_db
            db = get_db(RAG_DB)
            chunk_ids = [r["id"] for r in db.execute("SELECT id FROM chunks").fetchall()]
            for cid in chunk_ids:
                db.execute("DELETE FROM vec_chunks WHERE chunk_id = ?", (cid,))
            db.execute("DELETE FROM chunks")
            db.execute("DELETE FROM files")
            db.commit()
            db.close()
            results["actions"].append("deleted_all_documents")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"reset failed: {e}")

    if scope == "all":
        try:
            import shutil
            if os.path.exists(RAG_DB):
                shutil.move(RAG_DB, RAG_DB + ".bak")
            results["actions"].append("db_renamed_to_rag.db.bak")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"db rename failed: {e}")

    return results


@app.get("/api/system/backup")
def system_backup():
    """Download RAG DB backup with version metadata."""
    import shutil, json, time
    if not os.path.exists(RAG_DB):
        raise HTTPException(status_code=404, detail="no database to back up")
    backup_path = RAG_DB + ".backup"
    meta_path = RAG_DB + ".backup.meta"
    try:
        shutil.copy2(RAG_DB, backup_path)
        # Write metadata file
        meta = {"version": "0.1.0", "created": time.time(), "rag_db_size": os.path.getsize(RAG_DB)}
        with open(meta_path, "w") as f:
            json.dump(meta, f)
        # Cleanup both files in background
        def _cleanup():
            for p in [backup_path, meta_path]:
                if os.path.exists(p):
                    os.unlink(p)
        return FileResponse(backup_path, filename=f"m-acs-backup-v0.1.0-{int(time.time())}.db", media_type="application/octet-stream", background=BackgroundTask(_cleanup))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"backup failed: {e}")


@app.get("/api/system/startup")
def system_startup():
    """Startup integrity checks. Cached from first boot."""
    from services.startup import get_startup_status
    return get_startup_status()


@app.get("/api/system/backups")
def system_backups():
    """List available backups with metadata and version info."""
    import glob, json
    data_dir = os.path.dirname(RAG_DB) or "/data"
    backups = []
    seen_meta = {}
    # First pass: read all .meta files
    for mf in glob.glob(os.path.join(data_dir, "*.backup.meta")):
        try:
            with open(mf) as f:
                seen_meta[os.path.basename(mf).replace(".meta", "")] = json.load(f)
        except Exception:
            pass
    for f in sorted(glob.glob(os.path.join(data_dir, "*.bak")) + glob.glob(os.path.join(data_dir, "*.backup")), key=os.path.getmtime, reverse=True):
        try:
            entry = {
                "filename": os.path.basename(f),
                "size_bytes": os.path.getsize(f),
                "created": os.path.getmtime(f),
            }
            meta = seen_meta.get(os.path.basename(f))
            if meta:
                entry["version"] = meta.get("version", "unknown")
            backups.append(entry)
        except OSError:
            pass
    return {"backups": backups, "count": len(backups)}


@app.get("/api/system/preflight")
def system_preflight():
    """Deployment preflight checks. Run before install/upgrade."""
    import shutil
    import httpx
    checks = []
    all_ok = True

    # Disk space
    data_dir = os.path.dirname(RAG_DB) or "/data"
    try:
        usage = shutil.disk_usage(data_dir)
        free_gb = usage.free / (1024 ** 3)
        checks.append({"name": "disk_space", "status": "ok" if free_gb > 1 else "error", "detail": f"{free_gb:.1f} GB free on {data_dir}"})
        if free_gb <= 1:
            all_ok = False
    except Exception as e:
        checks.append({"name": "disk_space", "status": "error", "detail": str(e)})
        all_ok = False

    # Storage writable
    writable = os.access(data_dir, os.W_OK) if os.path.exists(data_dir) else False
    checks.append({"name": "storage_writable", "status": "ok" if writable else "error", "detail": f"{data_dir} {'writable' if writable else 'not writable'}"})
    if not writable:
        all_ok = False

    # Ollama reachable
    try:
        resp = httpx.get(f"{config.OLLAMA_URL}/", timeout=10)
        checks.append({"name": "ollama_reachable", "status": "ok" if resp.status_code == 200 else "error", "detail": "reachable" if resp.status_code == 200 else f"status {resp.status_code}"})
        if resp.status_code != 200:
            all_ok = False
    except Exception as e:
        checks.append({"name": "ollama_reachable", "status": "error", "detail": str(e)})
        all_ok = False

    # GPU available (via existing health)
    try:
        from services.gpu import get_gpu_metrics
        gpu = get_gpu_metrics()
        if gpu.get("status") == "unavailable":
            checks.append({"name": "gpu_available", "status": "warning", "detail": "GPU metrics unavailable — system may run without GPU"})
        else:
            checks.append({"name": "gpu_available", "status": "ok", "detail": gpu.get("name", "GPU detected")})
    except Exception as e:
        checks.append({"name": "gpu_available", "status": "warning", "detail": str(e)})

    # Port availability (control plane)
    import socket
    for port_name, port_num in [("dashboard", config.PORT), ("ollama", 11434)]:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(("0.0.0.0", port_num))
            sock.close()
            checks.append({"name": f"port_{port_num}", "status": "ok" if result != 0 else "warning", "detail": f"port {port_num} ({port_name}) {'in use' if result == 0 else 'available'}"})
        except Exception:
            pass

    return {"checks": checks, "all_ok": all_ok, "version": "0.1.0"}


@app.get("/api/system/support-bundle")
def system_support_bundle():
    """Export a comprehensive support/diagnostics bundle as JSON."""
    import httpx
    from services.startup import get_startup_status
    import json as _json
    import time

    bundle = {
        "version": "0.1.0",
        "generated": time.time(),
        "generated_human": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "system": {
            "platform": __import__("sys").platform,
            "python_version": __import__("sys").version,
        },
        "config": {
            "RAG_DB_PATH": config.RAG_DB_PATH,
            "RAG_EMBED_MODEL": config.RAG_EMBED_MODEL,
            "OLLAMA_URL": config.OLLAMA_URL,
            "GPU_METRICS_FILE": config.GPU_METRICS_FILE,
        },
    }

    # Startup checks
    bundle["startup"] = get_startup_status()

    # Health
    from services.health import get_health
    bundle["health"] = get_health()

    # Storage
    try:
        import os as _os
        db_size = _os.path.getsize(RAG_DB) if _os.path.exists(RAG_DB) else 0
        bundle["storage"] = {
            "rag_db_bytes": db_size,
            "rag_db_exists": _os.path.exists(RAG_DB),
        }
    except Exception as e:
        bundle["storage"] = {"error": str(e)}

    # Models via Ollama proxy
    try:
        resp = httpx.get(f"{config.OLLAMA_URL}/api/tags", timeout=10)
        if resp.status_code == 200:
            models = resp.json().get("models", [])
            bundle["models"] = {
                "count": len(models),
                "list": [{"name": m["name"], "size_gb": round(m.get("size", 0) / 1e9, 2)} for m in models],
            }
    except Exception as e:
        bundle["models"] = {"error": str(e)}

    # GPU
    try:
        from services.gpu import get_gpu_metrics
        bundle["gpu"] = get_gpu_metrics()
    except Exception as e:
        bundle["gpu"] = {"error": str(e)}

    return bundle


def fmt_size_human(b):
    if b is None: return "N/A"
    if b > 1e9: return f"{b/1e9:.1f} GB"
    if b > 1e6: return f"{b/1e6:.1f} MB"
    if b > 1e3: return f"{b/1e3:.0f} KB"
    return f"{b} B"


# Must be last — catch-all for static files
@app.get("/")
def index():
    return FileResponse(os.path.join(STATIC, "index.html"))
