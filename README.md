# M-ACS-1 — Professional Cognition Operating Environment

**Your private document intelligence appliance — deploy on any NVIDIA GPU machine in one command.**

M-ACS-1 is not a chatbot. It is a complete **Professional Cognition Operating Environment**: a locally deployed system where professional users upload documents, ask questions, organize evidence, build investigations, and control their analytical workflow — with AI used exclusively for retrieval.

```
裸 Ubuntu + NVIDIA 机器
    ↓ sudo ./install.sh
    ↓ ~15 分钟
浏览器打开 http://localhost:8080
    ↓ 上传文档 → 提问 → 分析
```

---

## Architecture Overview

```
                    ┌─────────────────────────────────────┐
                    │      Professional Cognition Layer     │
                    │  retrieval → evidence → topology     │
                    │  attention → flow → review → closure │
                    │  coordination → landscape → energy   │
                    └─────────────────────────────────────┘
                                      │
                    ┌─────────────────────────────────────┐
                    │      Operational System Layer        │
                    │  diagnostics → startup → recovery   │
                    │  backup → preflight → support       │
                    └─────────────────────────────────────┘
                                      │
              ┌───────────────────────┴───────────────────────┐
              │                                               │
    ┌─────────────────────┐                    ┌─────────────────────┐
    │   Ollama (AI Engine) │                    │  Control Plane      │
    │   local models       │                    │  Python FastAPI     │
    │   RAG embeddings     │                    │  sqlite-vec vectorDB│
    └─────────────────────┘                    └─────────────────────┘
```

### Design Principles

| Principle | Meaning |
|---|---|
| **Human reasons** | All analysis decisions belong to the user |
| **AI retrieves** | AI only finds relevant content from documents |
| **System stays deterministic** | Same input → same output, every time |
| **Coherence > Capability** | No feature expansion beyond cognition ergonomics |

---

## Features

### Cognition Layer (8 integrated systems)

| Layer | Function |
|---|---|
| **Retrieval** | RAG with token-budget, section-aware chunking, cross-query frequency |
| **Evidence** | Compare, pin, copy, source attribution, relevance scoring |
| **Topology** | Cross-document section mapping, cross-topic relationship view |
| **Attention** | Hot sections, unresolved filtering, compact mode, collapsed repetition |
| **Flow** | Query trail, topic branching, pivot detection, investigation timeline |
| **Review** | Per-chunk + per-query review (○→✓), review progress tracking |
| **Closure** | Open questions, milestones, branch lifecycle (reviewing→stable→done) |
| **Coordination** | Branch overview, energy signals, fatigue warnings, landscape bars |

### Operational Layer

| Feature | Endpoint |
|---|---|
| System diagnostics | `GET /api/system/diagnostics` |
| Startup integrity (6 checks) | `GET /api/system/startup` |
| Deployment preflight (5 checks) | `GET /api/system/preflight` |
| Backup with version metadata | `GET /api/system/backup` |
| Backup listing with version history | `GET /api/system/backups` |
| Safe reset (docs / full) | `POST /api/system/reset` |
| Support bundle export | `GET /api/system/support-bundle` |

### Supported Models

| Model | Size | Type |
|---|---|---|
| `qwen2.5:0.5b` | 397 MB | Fast test / Chinese |
| `llama3.2:3b` | ~2 GB | Balanced general |
| `deepseek-coder:6.7b` | ~4 GB | Code |
| `qwen2.5:7b` | ~4 GB | Chinese / general |
| `llama3.1:8b` | ~4.7 GB | Best quality |
| `bge-m3` | ~2 GB | Embeddings (RAG) |

---

## Quick Start

### Requirements

- **Ubuntu 22.04 or 24.04** (x86_64)
- **NVIDIA GPU** with CUDA-compatible driver
- **Network** (for first-time install; offline install supported)

### Installation

```bash
# Online install
curl -fsSL https://raw.githubusercontent.com/DitoSun/m-acs-1/master/install.sh | sudo bash

# Or from release tarball
git clone https://github.com/DitoSun/m-acs-1.git
cd m-acs-1
sudo ./install.sh
```

Installation is fully automated:
1. Detect GPU and install NVIDIA driver (with reboot prompt if needed)
2. Install Docker with GPU support
3. Start Ollama + Control Plane containers
4. Set up auto-start on boot

### First Use

Open **http://localhost:8080** in your browser.

1. Click a recommended model (e.g., Quick Start → `qwen2.5:0.5b`)
2. Wait for download (397 MB for quick test)
3. Upload a PDF document
4. Ask questions — see AI answers with source citations
5. Use the ⚙ panel for system health, startup checks, backups

---

## Offline Install

```bash
# On a machine with internet
cd m-acs-1
./release.sh 0.1.0
# Produces: m-acs-0.1.0.tar.gz + m-acs-0.1.0.sha256

# Copy to air-gapped machine, then:
tar zxf m-acs-0.1.0.tar.gz
cd m-acs-0.1.0
sudo ./install.sh
```

The installer automatically detects a release tarball alongside `install.sh`
and verifies SHA256 integrity before extraction.

---

## Operational Management

```bash
# Open the system panel in the dashboard
# Click ⚙ in the titlebar → shows: startup checks, storage, backups, diagnostics

# Create a backup
curl -o backup.db http://localhost:8080/api/system/backup
# → downloads m-acs-backup-v0.1.0-{timestamp}.db + .meta file

# Run diagnostics
curl http://localhost:8080/api/system/diagnostics

# Deployment preflight
curl http://localhost:8080/api/system/preflight

# Export support bundle
curl -o support.json http://localhost:8080/api/system/support-bundle

# Safe reset (clear all documents)
curl -X POST http://localhost:8080/api/system/reset \
  -H 'Content-Type: application/json' \
  -d '{"scope": "docs"}'
```

---

## Configuration

| Env Variable | Default | Description |
|---|---|---|
| `OLLAMA_URL` | `http://ollama:11434` | Ollama service URL |
| `RAG_DB_PATH` | `/data/rag.db` | Vector database path |
| `RAG_EMBED_MODEL` | `bge-m3` | Embedding model for RAG |
| `GPU_METRICS_FILE` | `/data/gpu.json` | GPU metrics from host-agent |
| `CONTROL_PLANE_PORT` | `8080` | Dashboard port |

---

## Project Status

| Metric | Value |
|---|---|
| Version | v0.1.0 |
| Architecture | Single-file SPA + Python FastAPI + sqlite-vec |
| Total LOC | ~3,400 (35% of 9,000 budget) |
| Frontend | 1 file, ~340 lines, all CSS/JS inline |
| Backend | 7 Python files |
| Dependencies | 0 frontend / 8 Python |
| Full-stack tests | 22/22 passed |

### Development Philosophy

```
User reasons.       → all analysis, judgment, workflow
AI retrieves.       → RAG document search only
System stays deterministic. → same input, same output
Coherence over capability.  → freeze on v1 architecture
```

---

## License

MIT
