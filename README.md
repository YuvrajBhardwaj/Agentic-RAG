# Agentic RAG — ask your docs anything 🤖📄

Upload PDFs → get sourced answers streamed in real time. A production-style **Retrieval-Augmented Generation** backend with an agent planner, vector search, and SSE streaming.

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat&logo=fastapi&logoColor=white)
![Groq](https://img.shields.io/badge/LLM-Groq-orange?style=flat)
![FAISS](https://img.shields.io/badge/Vector-FAISS-0467DF?style=flat)

> Built to show I can ship AI that businesses actually use: support bot over company docs, policy Q&A, research assistant. Swap the demo data for any docs and it just works.

## How it works

```
PDF / docs → extract + chunk → embed → FAISS ─┐
                                              ├→ agent planner → LLM (Groq) → streamed answer + sources
User question → semantic search ──────────────┘
```

- **Ingest** PDFs (up to 5 at once) or raw JSON docs
- **Retrieve** top-k chunks via FAISS + sentence-transformers
- **Answer** with an LLM grounded in retrieved context, citing sources
- **Stream** agent reasoning live over Server-Sent Events

## 60-second quickstart

```bash
git clone https://github.com/YuvrajBhardwaj/Agentic-RAG.git
cd Agentic-RAG
python -m venv .venv && source .venv/bin/activate  # .venv\Scripts\activate on Windows
pip install -r requirements.txt

cp .env.example .env   # then put your key in: GROQ_API_KEY=...
uvicorn app.main:app --reload
```

Open **http://localhost:8000/docs** for interactive Swagger UI, or open `index.html` for the demo chat frontend.

```bash
# ingest + ask (sync)
curl -X POST localhost:8000/ingest -H "Content-Type: application/json" \
  -d '{"docs":[{"id":"doc1","text":"RAG combines retrieval with generation","meta":{"source":"docs"}}]}'

curl -X POST localhost:8000/query -H "Content-Type: application/json" \
  -d '{"query":"What is RAG?","top_k":3}'

# ask with live reasoning stream
curl -X POST localhost:8000/query/stream -H "Content-Type: application/json" \
  -d '{"query":"What is RAG?","top_k":3}'
```

No API key? It still runs — retrieval, planning, streaming, and PDF upload all work, with a clearly-marked fallback answer until you add `GROQ_API_KEY`.

## Endpoints

| Method | Route | What |
|---|---|---|
| GET | `/health` | Status + doc count |
| GET | `/store-stats` | Index size, docs per source |
| POST | `/ingest` | Add JSON docs |
| POST | `/query` | Answer + sources (sync) |
| POST | `/query/stream` | Agent reasoning via SSE |
| POST | `/upload-pdf` | Upload up to 5 PDFs |
| POST | `/upload-pdf/stream` | PDF ingest with per-file SSE progress |

## Structure

```
app/
├── main.py            # FastAPI app + all endpoints
├── schemas.py         # Pydantic models
├── rag/store.py       # FAISS vector store (persisted to disk)
├── llm/groq_client.py # LLM wrapper (graceful fallback, no key needed to run)
└── agents/planner.py  # Agent planner + tool interface (retrieval, generation)
```

`verify_setup.py` checks your environment · `test_api.py` / `test_pdf_upload.py` exercise the endpoints · `examples/client.py` is a Python client reference.

## What's next

- [ ] ReAct-style LLM planning (currently rule-based — easy to extend via the `Tool` interface)
- [ ] Multi-agent delegation (supervisor → specialists)
- [ ] Web-search + code-execution tools
- [ ] Pinecone/Weaviate swap for large-scale deploys
