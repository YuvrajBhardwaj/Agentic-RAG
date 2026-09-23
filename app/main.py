import json, os, re, uuid, asyncio, tempfile, time, threading
from typing import List, AsyncGenerator, Dict, Optional
from fastapi import FastAPI, HTTPException, UploadFile, File, Request, Header, Depends
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from .schemas import IngestRequest, QueryRequest, QueryResponse, StoreStats
from .rag.store import VectorStore
from .llm.groq_client import generate
from .agents.planner import AgentPlanner, RetrievalTool, GenerationTool
from .utils.pdf_processor import extract_text_from_pdf, chunk_text

load_dotenv()

app = FastAPI(title="Agentic RAG")

# ── Config ────────────────────────────────────────────────
DATA_DIR = os.environ.get("RAG_DATA_DIR", "data")
API_KEY = os.environ.get("RAG_API_KEY", "").strip()
RATE_LIMIT_PER_MIN = int(os.environ.get("RATE_LIMIT_PER_MIN", "60"))
MAX_PDF_MB = int(os.environ.get("MAX_PDF_MB", "15"))
MAX_PDF_BYTES = MAX_PDF_MB * 1024 * 1024

_raw_origins = os.environ.get("ALLOWED_ORIGINS", "").strip()
if _raw_origins:
    ALLOWED_ORIGINS = [o.strip() for o in _raw_origins.split(",") if o.strip()]
elif API_KEY:
    # Locked down by default once an API key is set
    ALLOWED_ORIGINS = [
        "https://webdev-uv.netlify.app",
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8000",
    ]
else:
    ALLOWED_ORIGINS = ["*"]  # dev only (no API key set)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False if ALLOWED_ORIGINS == ["*"] else True,
    allow_methods=["*"],
    allow_headers=["*", "X-API-Key", "X-Tenant-ID"],
)

# ── Auth (optional, enforced when RAG_API_KEY is set) ─────
PUBLIC_PATHS = {"/health", "/docs", "/redoc", "/openapi.json"}


def require_api_key(request: Request, x_api_key: Optional[str] = Header(None)):
    if not API_KEY:
        return  # dev mode: open
    if request.url.path in PUBLIC_PATHS:
        return
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing X-API-Key")


# ── Rate limit (simple per-IP sliding window, no extra deps) ─
_hits: Dict[str, List[float]] = {}
_hits_lock = threading.Lock()


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    if request.url.path in PUBLIC_PATHS:
        return await call_next(request)
    if RATE_LIMIT_PER_MIN <= 0:
        return await call_next(request)
    ip = request.client.host if request.client else "unknown"
    now = time.time()
    window_start = now - 60
    with _hits_lock:
        bucket = _hits.get(ip, [])
        bucket = [t for t in bucket if t > window_start]
        if len(bucket) >= RATE_LIMIT_PER_MIN:
            raise HTTPException(status_code=429, detail="Rate limit exceeded. Slow down.")
        bucket.append(now)
        _hits[ip] = bucket
    return await call_next(request)


# ── Multi-tenant stores (one FAISS dir per tenant) ────────
TENANT_RE = re.compile(r"[^a-zA-Z0-9_-]")
_stores: Dict[str, VectorStore] = {}
_stores_lock = threading.Lock()


def sanitize_tenant(raw: Optional[str]) -> str:
    t = (raw or "default").strip() or "default"
    t = TENANT_RE.sub("-", t)[:64]
    return t or "default"


def get_store(tenant: str) -> VectorStore:
    with _stores_lock:
        if tenant not in _stores:
            _stores[tenant] = VectorStore(persist_dir=os.path.join(DATA_DIR, tenant))
        return _stores[tenant]


def resolve_tenant(
    request: Request,
    x_tenant_id: Optional[str] = Header(None),
) -> str:
    # Header wins; body/query fallback handled per-endpoint
    return sanitize_tenant(x_tenant_id)


def build_planner(store: VectorStore) -> AgentPlanner:
    return AgentPlanner(tools=[RetrievalTool(store), GenerationTool(generate)])


def ingest_text_as_chunks(store: VectorStore, text: str, filename: str, page_count: int) -> tuple[str, int]:
    """Split text into chunks and store each chunk as its own vector. Returns (parent_doc_id, n_chunks)."""
    chunks = chunk_text(text)
    if not chunks:
        raise ValueError("No extractable text found")
    parent_id = f"pdf-{uuid.uuid4().hex[:8]}-{filename.replace('.pdf', '')[:40]}"
    docs = [
        dict(
            id=f"{parent_id}#c{i}",
            text=chunk,
            meta=dict(
                source="pdf",
                filename=filename,
                pages=page_count,
                parent_id=parent_id,
                chunk_index=i,
                chunk_count=len(chunks),
            ),
        )
        for i, chunk in enumerate(chunks)
    ]
    store.add_documents(docs)
    return parent_id, len(chunks)


# ── Health ──────────────────────────────────────────────
@app.get("/health")
def health():
    with _stores_lock:
        tenants = list(_stores.keys())
    total = sum(len(s.metadatas) for s in _stores.values())
    return {
        "status": "healthy",
        "version": "0.3.0",
        "documents": total,
        "tenants_loaded": len(tenants),
        "auth": "enforced" if API_KEY else "open-dev",
    }


# ── Store stats ─────────────────────────────────────────
@app.get("/store-stats", response_model=StoreStats, dependencies=[Depends(require_api_key)])
def store_stats(request: Request, x_tenant_id: Optional[str] = Header(None)):
    tenant = resolve_tenant(request, x_tenant_id)
    store = get_store(tenant)
    sources = {}
    for m in store.metadatas:
        src = m.get("meta", {}).get("source", "unknown")
        sources[src] = sources.get(src, 0) + 1
    return StoreStats(
        total_documents=len(store.metadatas),
        index_size=store.index.ntotal if store.index else 0,
        sources=sources,
    )


# ── Ingest ──────────────────────────────────────────────
@app.post("/ingest", dependencies=[Depends(require_api_key)])
def ingest(req: IngestRequest, request: Request, x_tenant_id: Optional[str] = Header(None)):
    tenant = sanitize_tenant(req.tenant_id or x_tenant_id)
    store = get_store(tenant)
    try:
        docs = [d.model_dump() for d in req.docs]
        store.add_documents(docs)
        return {"status": "ok", "ingested": len(docs), "total": len(store.metadatas), "tenant": tenant}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Query ───────────────────────────────────────────────
@app.post("/query", response_model=QueryResponse, dependencies=[Depends(require_api_key)])
def query(req: QueryRequest, request: Request, x_tenant_id: Optional[str] = Header(None)):
    tenant = sanitize_tenant(req.tenant_id or x_tenant_id)
    store = get_store(tenant)
    try:
        k = max(1, min(req.top_k or 5, 20))
        hits = store.similarity_search(req.query, k=k)
        sources = [{"id": h.get("id"), "meta": h.get("meta")} for h in hits]
        context = "\n".join(
            f"[Source {i+1}]\n{h.get('text', '')}\n"
            for i, h in enumerate(hits)
        )
        prompt = (
            "You are an assistant that answers user queries using provided context.\n"
            f"Context:\n{context}\n"
            f"User question: {req.query}\n"
            "Answer concisely, citing sources by index when appropriate."
        )
        answer = generate(prompt)
        return QueryResponse(answer=answer, sources=sources)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Query stream ────────────────────────────────────────
@app.post("/query/stream", dependencies=[Depends(require_api_key)])
async def query_stream(req: QueryRequest, request: Request, x_tenant_id: Optional[str] = Header(None)):
    tenant = sanitize_tenant(req.tenant_id or x_tenant_id)
    store = get_store(tenant)
    planner = build_planner(store)

    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            plan = planner.plan(req.query)
            yield f"data: {json.dumps({'event': 'plan_start', 'goal': req.query, 'steps': len(plan.steps), 'tenant': tenant})}\n\n"
            await asyncio.sleep(0.01)
            for step_result in planner.execute_plan(plan):
                yield f"data: {json.dumps({'event': 'step', 'message': step_result.strip()})}\n\n"
                await asyncio.sleep(0.01)
            yield f"data: {json.dumps({'event': 'plan_complete', 'status': 'success'})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'event': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# ── PDF upload (single batch) ───────────────────────────
@app.post("/upload-pdf", dependencies=[Depends(require_api_key)])
async def upload_pdf(
    request: Request,
    files: List[UploadFile] = File(...),
    x_tenant_id: Optional[str] = Header(None),
):
    tenant = resolve_tenant(request, x_tenant_id)
    store = get_store(tenant)
    if len(files) > 5:
        raise HTTPException(status_code=400, detail="Maximum 5 files allowed")

    results = []
    for file in files:
        filename = file.filename or "unnamed"
        try:
            if not filename.lower().endswith(".pdf"):
                results.append(dict(filename=filename, status="error", error="Not a PDF", pages=0, chunks=0))
                continue

            content = await file.read()
            if len(content) > MAX_PDF_BYTES:
                results.append(dict(filename=filename, status="error", error=f"File exceeds {MAX_PDF_MB}MB", pages=0, chunks=0))
                continue
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(content)
                tmp_path = tmp.name

            try:
                text, page_count = extract_text_from_pdf(tmp_path)
                if not text.strip():
                    raise ValueError("No extractable text found")

                # FIX: store each chunk as its own vector (was: whole PDF as 1 vector)
                doc_id, n_chunks = ingest_text_as_chunks(store, text, filename, page_count)

                results.append(dict(
                    filename=filename, status="success",
                    doc_id=doc_id, pages=page_count, chunks=n_chunks,
                    text_length=len(text),
                ))
            finally:
                os.unlink(tmp_path)

        except Exception as e:
            results.append(dict(filename=filename, status="error", error=str(e), pages=0, chunks=0))

    ok = sum(1 for r in results if r["status"] == "success")
    return {"total": len(files), "successful": ok, "failed": len(files) - ok, "results": results, "tenant": tenant}


# ── PDF upload (SSE stream per file) ────────────────────
@app.post("/upload-pdf/stream", dependencies=[Depends(require_api_key)])
async def upload_pdf_stream(
    request: Request,
    files: List[UploadFile] = File(...),
    x_tenant_id: Optional[str] = Header(None),
):
    tenant = resolve_tenant(request, x_tenant_id)
    store = get_store(tenant)
    if len(files) > 5:
        raise HTTPException(status_code=400, detail="Maximum 5 files allowed")

    async def event_generator() -> AsyncGenerator[str, None]:
        yield f"data: {json.dumps({'event': 'batch_start', 'total': len(files), 'tenant': tenant})}\n\n"
        await asyncio.sleep(0.01)
        succeeded = 0

        for idx, file in enumerate(files):
            filename = file.filename or "unnamed"
            try:
                if not filename.lower().endswith(".pdf"):
                    yield f"data: {json.dumps({'event': 'file_error', 'index': idx, 'filename': filename, 'error': 'Not a PDF'})}\n\n"
                    continue

                yield f"data: {json.dumps({'event': 'file_start', 'index': idx, 'filename': filename})}\n\n"
                await asyncio.sleep(0.01)

                content = await file.read()
                if len(content) > MAX_PDF_BYTES:
                    yield f"data: {json.dumps({'event': 'file_error', 'index': idx, 'filename': filename, 'error': f'File exceeds {MAX_PDF_MB}MB'})}\n\n"
                    continue
                yield f"data: {json.dumps({'event': 'file_reading', 'index': idx, 'filename': filename, 'bytes': len(content)})}\n\n"
                await asyncio.sleep(0.01)

                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                    tmp.write(content)
                    tmp_path = tmp.name

                try:
                    yield f"data: {json.dumps({'event': 'file_extracting', 'index': idx, 'filename': filename})}\n\n"
                    await asyncio.sleep(0.01)

                    text, page_count = extract_text_from_pdf(tmp_path)
                    if not text.strip():
                        raise ValueError("No extractable text found")

                    chunks = chunk_text(text)
                    yield f"data: {json.dumps({'event': 'file_embedding', 'index': idx, 'filename': filename, 'pages': page_count, 'chunks': len(chunks)})}\n\n"
                    await asyncio.sleep(0.01)

                    # FIX: chunk-level vectors
                    doc_id, n_chunks = ingest_text_as_chunks(store, text, filename, page_count)
                    succeeded += 1

                    yield f"data: {json.dumps({'event': 'file_done', 'index': idx, 'filename': filename, 'doc_id': doc_id, 'pages': page_count, 'chunks': n_chunks})}\n\n"
                finally:
                    os.unlink(tmp_path)

            except Exception as e:
                yield f"data: {json.dumps({'event': 'file_error', 'index': idx, 'filename': filename, 'error': str(e)})}\n\n"

            await asyncio.sleep(0.01)

        yield f"data: {json.dumps({'event': 'batch_done', 'total': len(files), 'successful': succeeded})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
