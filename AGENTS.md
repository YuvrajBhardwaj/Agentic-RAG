# Agentic RAG — AGENTS.md

## Quick commands
```bash
.\.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
python verify_setup.py      # pre-flight check
python demo.py              # demo (uses demo_data/, not data/)
```

## Tests
No pytest. Tests are standalone scripts that expect a running server on port 8000:
```bash
python test_api.py          # integration: health / ingest / query / stream
python test_gemini.py       # LLM call only
python test_pdf_upload.py   # PDF upload + query (needs reportlab for sample PDF)
```
Run server first, then test. Tests use `requests` (not httpx, not TestClient).

## Architecture
```
app/main.py               — FastAPI app, 5 endpoints
app/schemas.py             — Pydantic models (Doc, IngestRequest, QueryRequest, etc.)
app/rag/store.py           — FAISS + sentence-transformers vector store
app/llm/gemini_client.py   — Gemini API wrapper with fallback generation
app/agents/planner.py      — Agent planner with tool interface (RetrievalTool, GenerationTool)
app/utils/pdf_processor.py — PyPDF2 extraction + text chunking
index.html                 — Standalone HTML/JS UI (no build step)
```

## Key gotchas
- **Gemini quota exhausted** → `gemini_client.py` silently falls back to a template-based response. Not an error. Check server logs for `warnings.warn`.
- **Windows paths** everywhere: `run.sh`, `run_server.py`, `SETUP.md`. Never use `/` for project paths.
- **`.env` contains a live API key** (see `SETUP.md:35`). `data/` and `.env` are gitignored — do not accidentally commit.
- **Embedding model** defaults to `all-MiniLM-L6-v2`, override via `EMBEDDING_MODEL` env var.
- **Vector store** persists to `data/faiss.index` + `data/meta.json`. Delete these to reset.
- **No lint / typecheck / formatter config** exists. No CI pipeline.

## API endpoints
| Method | Path | Notes |
|--------|------|-------|
| GET | `/health` | Returns status + doc count |
| GET | `/store-stats` | Doc count, index size, sources breakdown |
| POST | `/ingest` | JSON body with `{docs: [{id, text, meta}]}` |
| POST | `/query` | Sync: `{query, top_k}` → `{answer, sources}` |
| POST | `/query/stream` | SSE stream: `plan_start` → `step` → `plan_complete` |
| POST | `/upload-pdf` | Multipart, max 5 files, returns batch result |
| POST | `/upload-pdf/stream` | Multipart, SSE per-file progress |

## Style notes
- `from .module import X` (relative imports, package is `app`)
- Pydantic v2 (`model_dump()`, not `.dict()`)
- Gemini model in `.env` is `gemini-3.5-flash`; `.env.example` says `gemini-2.0-flash` (stale)
