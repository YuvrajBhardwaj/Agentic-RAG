import json, os, uuid, asyncio, tempfile
from typing import List, AsyncGenerator
from fastapi import FastAPI, HTTPException, UploadFile, File, Query
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

from .schemas import IngestRequest, QueryRequest, QueryResponse, StoreStats
from .rag.store import VectorStore
from .llm.groq_client import generate
from .agents.planner import AgentPlanner, RetrievalTool, GenerationTool
from .utils.pdf_processor import extract_text_from_pdf, chunk_text

app = FastAPI(title="Agentic RAG")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_DIR = os.environ.get("RAG_DATA_DIR", "data")
store = VectorStore(persist_dir=DATA_DIR)

tools = [RetrievalTool(store), GenerationTool(generate)]
planner = AgentPlanner(tools=tools)


# ── Health ──────────────────────────────────────────────

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "version": "0.2.0",
        "documents": len(store.metadatas),
    }


# ── Store stats ─────────────────────────────────────────

@app.get("/store-stats", response_model=StoreStats)
def store_stats():
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

@app.post("/ingest")
def ingest(req: IngestRequest):
    try:
        docs = [d.model_dump() for d in req.docs]
        store.add_documents(docs)
        return {"status": "ok", "ingested": len(docs), "total": len(store.metadatas)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Query ───────────────────────────────────────────────

@app.post("/query", response_model=QueryResponse)
def query(req: QueryRequest):
    try:
        k = req.top_k or 5
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

@app.post("/query/stream")
async def query_stream(req: QueryRequest):
    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            plan = planner.plan(req.query)
            yield f"data: {json.dumps({'event': 'plan_start', 'goal': req.query, 'steps': len(plan.steps)})}\n\n"
            await asyncio.sleep(0.01)
            for step_result in planner.execute_plan(plan):
                yield f"data: {json.dumps({'event': 'step', 'message': step_result.strip()})}\n\n"
                await asyncio.sleep(0.01)
            yield f"data: {json.dumps({'event': 'plan_complete', 'status': 'success'})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'event': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# ── PDF upload (single batch) ───────────────────────────

@app.post("/upload-pdf")
async def upload_pdf(files: List[UploadFile] = File(...)):
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
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(content)
                tmp_path = tmp.name

            try:
                text, page_count = extract_text_from_pdf(tmp_path)
                if not text.strip():
                    raise Exception("No extractable text found")

                chunks = chunk_text(text)
                doc_id = f"pdf-{uuid.uuid4().hex[:8]}-{filename.replace('.pdf', '')}"
                store.add_documents([dict(
                    id=doc_id,
                    text=text,
                    meta=dict(source="pdf", filename=filename, pages=page_count, chunks=len(chunks)),
                )])

                results.append(dict(
                    filename=filename, status="success",
                    doc_id=doc_id, pages=page_count, chunks=len(chunks),
                    text_length=len(text),
                ))
            finally:
                os.unlink(tmp_path)

        except Exception as e:
            results.append(dict(filename=filename, status="error", error=str(e), pages=0, chunks=0))

    ok = sum(1 for r in results if r["status"] == "success")
    return {"total": len(files), "successful": ok, "failed": len(files) - ok, "results": results}


# ── PDF upload (SSE stream per file) ────────────────────

@app.post("/upload-pdf/stream")
async def upload_pdf_stream(files: List[UploadFile] = File(...)):
    if len(files) > 5:
        raise HTTPException(status_code=400, detail="Maximum 5 files allowed")

    async def event_generator() -> AsyncGenerator[str, None]:
        yield f"data: {json.dumps({'event': 'batch_start', 'total': len(files)})}\n\n"
        await asyncio.sleep(0.01)

        for idx, file in enumerate(files):
            filename = file.filename or "unnamed"
            try:
                if not filename.lower().endswith(".pdf"):
                    yield f"data: {json.dumps({'event': 'file_error', 'index': idx, 'filename': filename, 'error': 'Not a PDF'})}\n\n"
                    continue

                yield f"data: {json.dumps({'event': 'file_start', 'index': idx, 'filename': filename})}\n\n"
                await asyncio.sleep(0.01)

                content = await file.read()
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
                        raise Exception("No extractable text found")

                    chunks = chunk_text(text)
                    yield f"data: {json.dumps({'event': 'file_embedding', 'index': idx, 'filename': filename, 'pages': page_count, 'chunks': len(chunks)})}\n\n"
                    await asyncio.sleep(0.01)

                    doc_id = f"pdf-{uuid.uuid4().hex[:8]}-{filename.replace('.pdf', '')}"
                    store.add_documents([dict(
                        id=doc_id, text=text,
                        meta=dict(source="pdf", filename=filename, pages=page_count, chunks=len(chunks)),
                    )])

                    yield f"data: {json.dumps({'event': 'file_done', 'index': idx, 'filename': filename, 'doc_id': doc_id, 'pages': page_count, 'chunks': len(chunks)})}\n\n"
                finally:
                    os.unlink(tmp_path)

            except Exception as e:
                yield f"data: {json.dumps({'event': 'file_error', 'index': idx, 'filename': filename, 'error': str(e)})}\n\n"

            await asyncio.sleep(0.01)

        ok = len([r for r in []])  # placeholder – we just stream events
        yield f"data: {json.dumps({'event': 'batch_done', 'total': len(files)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
