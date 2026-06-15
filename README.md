# Agentic RAG — FastAPI backend (Python)

Production-ready Agentic RAG backend using FastAPI, FAISS, sentence-transformers, and a pluggable Gemini client. Features include:
- **Vector store** (FAISS + sentence-transformers) for semantic search
- **Agent planner** with tool interface (retrieval, generation, reasoning)
- **SSE streaming** for real-time agentic responses
- **Modular design** for easy extension and multi-agent orchestration

## Quickstart

### 1. Setup Environment

```bash
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
```

### 2. Configure Gemini API

Create `.env` file (already included, just verify):

```
GEMINI_API_KEY=your_api_key_here
GEMINI_MODEL=gemini-3.5-flash
RAG_DATA_DIR=data
```

Or use the existing one with your API key.

### 3. Verify Setup

```bash
python verify_setup.py
```

### 4. Start Server

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Server will be available at: `http://localhost:8000`
- API Docs (Swagger): `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### 5. Test Endpoints

**Health Check:**
```bash
curl http://localhost:8000/health
```

**Ingest Documents:**
```bash
curl -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "docs": [
      {
        "id": "doc1",
        "text": "RAG combines retrieval with generation",
        "meta": {"source": "docs"}
      }
    ]
  }'
```

**Query (Sync):**
```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is RAG?", "top_k": 3}'
```

**Query (Streaming via SSE):**
```bash
curl -X POST http://localhost:8000/query/stream \
  -H "Content-Type: application/json" \
  -d '{"query": "What is RAG?", "top_k": 3}'
```

**Using Python Client:**
```bash
python examples/client.py --ingest
python examples/client.py --query "What is RAG?"
python examples/client.py --stream-query "What is RAG?"
```

## Endpoints

### Health
- `GET /health` — Returns server status

### Ingestion
- `POST /ingest` — Ingest documents
  ```json
  {
    "docs": [
      {"id": "doc1", "text": "...", "meta": {"source": "confluence"}}
    ]
  }
  ```

### Query (Synchronous)
- `POST /query` — Get answer with sources
  ```json
  {
    "query": "What is the RAG system?",
    "top_k": 5
  }
  ```
  Response:
  ```json
  {
    "answer": "...",
    "sources": [{"id": "doc1", "meta": {...}}]
  }
  ```

### Query (Streaming via SSE)
- `POST /query/stream` — Real-time agentic reasoning with Server-Sent Events
  ```bash
  curl -X POST http://localhost:8000/query/stream \
    -H "Content-Type: application/json" \
    -d '{"query": "What is RAG?", "top_k": 5}'
  ```
  Events streamed:
  - `plan_start` — Agent plan initialized
  - `step` — Each tool execution step
  - `plan_complete` — Plan finished

## Architecture

```
app/
├── main.py              # FastAPI app, endpoints
├── schemas.py           # Pydantic models (Doc, IngestRequest, QueryRequest, etc.)
├── rag/
│   ├── store.py         # VectorStore (FAISS + embedding model)
├── llm/
│   ├── gemini_client.py # Gemini API wrapper
└── agents/
    ├── planner.py       # AgentPlanner, Tool interface, tool implementations
```

## Modern Techniques Showcased

1. **Semantic search** with FAISS and sentence-transformers
2. **Agentic patterns**: Planning, tool use, step-by-step reasoning
3. **Real-time streaming** (SSE) for responsive user experience
4. **Vector store persistence** (JSON + FAISS index on disk)
5. **Modular tool interface** for easy addition of custom tools

## Next Steps (Extensions)

- Add more tools (web search, code execution, document parsing)
- Implement multi-agent delegation (Supervisor → Specialist Agents)
- Add memory/context window management
- Integrate n8n/Flowise nodes for workflow orchestration
- Deploy on VPS with PM2 + Nginx + Cloudflare CDN
- Add Pinecone/Weaviate for large-scale deployments

## Notes

- The Gemini client wrapper expects a Bearer token (OAuth access token). If you have an API key instead, adapt the client in `app/llm/gemini_client.py` to your auth method.
- The agent planner is intentionally simple for clarity; extend with LLM-based planning or ReAct patterns as needed.
- SSE streaming is production-ready; consider adding heartbeat/keep-alive for long-running tasks.

## Creator

Yuvraj Bhardwaj — Full-Stack Gen-AI Engineer  
Specialized in agentic RAG systems, SSE streaming, and enterprise AI infrastructure
