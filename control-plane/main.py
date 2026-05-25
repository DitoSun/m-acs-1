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


@app.post("/api/documents/ask")
def ask_documents(data: dict):
    """Ask a question against ingested documents."""
    question = data.get("question", "").strip()
    if not question:
        raise HTTPException(status_code=400, detail="question is required")
    file_ids = data.get("file_ids")  # optional

    from rag.retriever import retrieve, format_context, format_sources

    try:
        chunks = retrieve(RAG_DB, config.OLLAMA_URL, question, file_ids)
    except Exception as e:
        logger.exception("retrieval failed")
        raise HTTPException(status_code=500, detail=str(e))

    if not chunks:
        return {"answer": "未找到相关文档内容", "sources": []}

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

    sources = format_sources(chunks)
    return {"answer": answer, "sources": sources}


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


# Must be last — catch-all for static files
@app.get("/")
def index():
    return FileResponse(os.path.join(STATIC, "index.html"))
