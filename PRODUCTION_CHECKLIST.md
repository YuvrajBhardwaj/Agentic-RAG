# Production Checklist — Agentic RAG v0.3.0

What this PR (`prod-hardening`) fixes and what YOU must still do before charging clients.

## ✅ Fixed in code

- [x] **Leaked Gemini key removed** from `SETUP.md:35` → placeholder. Docs now Groq-first (matches `app/main.py`).
- [x] **Chunk-ingest bug** — `upload-pdf` + `upload-pdf/stream` stored the whole PDF as 1 vector. Now each chunk is its own vector with `parent_id / chunk_index / chunk_count` (`app/main.py:ingest_text_as_chunks`). Recall on real docs goes from ~useless to working.
- [x] **Tenant isolation** — `X-Tenant-ID` header (or `tenant_id` body field) → separate `RAG_DATA_DIR/<tenant>/` FAISS index. Sanitized, max 64 chars. No more cross-client doc leaks.
- [x] **API-key auth** — set `RAG_API_KEY`, all routes except `/health` + docs require `X-API-Key`. Open-dev mode when unset (with warning in `/health`).
- [x] **CORS lockdown** — `ALLOWED_ORIGINS` env. Defaults to your portfolio + localhost once a key is set; `*` only in dev. `allow_credentials` fixed (was `True` + `*`, which browsers reject).
- [x] **Rate limit** — `RATE_LIMIT_PER_MIN` (default 60/IP/min, in-memory sliding window, no new deps). Returns 429.
- [x] **Upload caps** — `MAX_PDF_MB` (default 15MB) enforced before parsing.
- [x] **Thread safety** — `VectorStore` writes under a lock; per-tenant store cache under a lock.
- [x] **Docker** — non-root `Dockerfile` + `.dockerignore` + `docker-compose.yml` (persistent `rag-data` volume, `--env-file`, healthcheck). Removed `COPY .env .env` anti-pattern from docs.
- [x] **Portability** — `run_server.py` no longer hardcodes `c:\Users\...`; `index.html` uses `window.RAG_API_BASE` override instead of hardcoded localhost.
- [x] **Tests** — `tests/test_production.py` (`pytest -q`): auth open/locked, tenant isolation, chunk-split regression. No model download needed.
- [x] **Config** — `.env.example` unified (Groq default + optional Gemini + hardening vars). `requirements.txt`: pydantic v2 floor + `httpx/pytest` for tests.

## 🔴 Do manually (I can't do these for you)

1. **Rotate the leaked Gemini key NOW** — Google AI Studio → API keys → delete `AIzaSyA7ON...`. It was in git history (`SETUP.md:35`). Check usage/billing for abuse.
2. **Purge history (optional but recommended):** `git filter-repo` or BFG on `SETUP.md`, or at minimum confirm the key is dead. Current PR removes it going forward, not from past commits.
3. **Set production env:**
   ```
   GROQ_API_KEY=...
   RAG_API_KEY=<openssl rand -hex 32>
   ALLOWED_ORIGINS=https://webdev-uv.netlify.app,https://<your-demo-domain>
   RAG_DATA_DIR=/app/data
   RATE_LIMIT_PER_MIN=60
   ```
4. **Deploy:** `docker compose up --build -d` on Hetzner/VPS + Cloudflare in front. Point `window.RAG_API_BASE` in `index.html` (or your Next.js frontend) at the API.
5. **Demo tenants:** ingest sample docs once per client with `X-Tenant-ID: demo-acme`, then share read-only demo key.

## 🟡 Still not production (next PRs)

- FAISS `IndexFlatL2` is single-node; move to pgvector/Qdrant with real namespaces + deletes for >100k chunks.
- No chat history, reranking, hybrid search, or faithfulness evals (see `SETUP.md` Level 4).
- Rate limit is per-instance memory — use Redis for multi-replica.
- No audit logging / metering per tenant (needed for billing).
- SSE has no heartbeat; add keep-alive for long streams behind Cloudflare/Nginx.

## Verify

```bash
pip install -r requirements.txt
pytest -q
uvicorn app.main:app --reload
# health (open) → {"status":"healthy","auth":"open-dev",...}
# with RAG_API_KEY set: curl -H "X-API-Key: ..." localhost:8000/store-stats -H "X-Tenant-ID: demo"
```
