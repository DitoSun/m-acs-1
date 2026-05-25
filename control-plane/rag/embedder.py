"""Embedding via Ollama /api/embed."""

import json
import logging
from urllib.request import Request, urlopen
from urllib.error import URLError

logger = logging.getLogger("m-acs.rag.embedder")

BATCH_SIZE = 16  # max inputs per /api/embed call


def embed_texts(texts: list[str], ollama_url: str, model: str = "bge-m3") -> list[list[float]]:
    """Embed a list of texts using Ollama. Returns list of embedding vectors."""
    all_embeddings = []

    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i:i + BATCH_SIZE]
        try:
            req = Request(
                f"{ollama_url}/api/embed",
                data=json.dumps({"model": model, "input": batch}).encode(),
                headers={"Content-Type": "application/json"},
            )
            with urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read())
                all_embeddings.extend(data["embeddings"])
        except (URLError, OSError, json.JSONDecodeError) as e:
            logger.warning("embedding batch %d failed: %s", i // BATCH_SIZE, e)
            raise

    return all_embeddings
