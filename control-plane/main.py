import json as _json
import logging
import os

from fastapi import FastAPI, HTTPException, Request
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
