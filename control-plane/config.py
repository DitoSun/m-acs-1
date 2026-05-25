"""Centralized config. Evaluated once at import: values from env or defaults."""

import os


class _Config:
    # -- Ollama --
    OLLAMA_URL: str = os.getenv("OLLAMA_URL", "http://ollama:11434")

    # -- GPU Metrics --
    GPU_METRICS_FILE: str = os.getenv("GPU_METRICS_FILE", "/data/gpu.json")
    METRICS_STALE_SECONDS: int = int(os.getenv("METRICS_STALE_SECONDS", "5"))

    # -- Control Plane --
    HOST: str = os.getenv("CONTROL_PLANE_HOST", "0.0.0.0")
    PORT: int = int(os.getenv("CONTROL_PLANE_PORT", "8080"))

    # -- RAG --
    RAG_DB_PATH: str = os.getenv("RAG_DB_PATH", "/data/rag.db")
    RAG_EMBED_MODEL: str = os.getenv("RAG_EMBED_MODEL", "bge-m3")


config = _Config()
