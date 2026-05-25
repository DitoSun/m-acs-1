# Changelog

## v0.1.0 (2026-05-25)

### Added
- One-command install (`install.sh`) with automatic GPU detection
- Dashboard with macOS-style UI
  - GPU monitor (temperature, VRAM, utilization)
  - System health panel
  - Model management (install, delete, recommended tabs)
  - Chat testing interface
- Professional Document Intelligence Pipeline
  - PDF ingestion (PyMuPDF)
  - Chinese + English legal chunking with clause boundary preservation
  - bge-m3 embedding via Ollama `/api/embed`
  - sqlite-vec vector storage
  - Token-budget retrieval with source attribution
- Document Workspace UI
  - PDF upload with processing status
  - Document Q&A with source citations
  - Expandable chunk previews
- 47-item benchmark suite (`benchmark.py`)
- 4-class professional document corpus (`corpus.py`)
- Debug bundle (`collect-debug.sh`) for issue reporting
- Full issue templates for GitHub
- Documentation: FAQ, Known Issues, Feedback, Release Checklist

### Infrastructure
- Docker Compose with Ollama + control-plane
- Host-agent for GPU metrics collection
- Systemd auto-start with crash-loop protection
- Docker Hub mirror fallback for China network
- IPv4 fallback for WSL2 environments

### Fixed
- PDF parser: null-byte and full-width character normalization
- Chunker: English and Chinese clause boundary detection
- Chunker: removed content duplication from overlap logic
- sqlite-vec: manual cascade delete for orphan vectors
- Chat: streaming buffer truncation causing content repetition
- Docker: version pinning format for Ubuntu Noble
