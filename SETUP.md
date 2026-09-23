# Agentic RAG - Complete Setup & Deployment Guide

## Project Summary

This is a **production-ready Agentic RAG system** built with:
- **Backend**: FastAPI (Python) with async support
- **Vector Store**: FAISS + sentence-transformers for semantic search
- **LLM**: Google Gemini API (gemini-3.5-flash)
- **Agent Planner**: Tool-use pattern with real-time SSE streaming
- **Modern Techniques**: ReAct-inspired agentic reasoning, streaming UI updates

## Quick Start (5 minutes)

### Step 1: Install Dependencies
```bash
# Navigate to project
cd "Agentic RAG"

# Create virtual environment
python -m venv .venv

# Activate venv
# On Windows:
.\.venv\Scripts\activate
# On Mac/Linux:
source .venv/bin/activate

# Install all packages
pip install -r requirements.txt
```

### Step 2: Configure API Key
Copy the template and add your own key (never commit `.env`):
```bash
cp .env.example .env
```
```
# LLM (Groq is the default — app/main.py uses groq_client)
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=mixtral-8x7b-32768
# Optional legacy Gemini path (demo.py only)
# GEMINI_API_KEY=your_gemini_key_here
# GEMINI_MODEL=gemini-2.0-flash
RAG_DATA_DIR=data
# Optional production hardening (see PRODUCTION_CHECKLIST.md)
# RAG_API_KEY=your_long_random_service_key
# ALLOWED_ORIGINS=https://your-frontend.com
# RATE_LIMIT_PER_MIN=60
```

> ⚠️ **Security:** if you ever pasted a real key into docs/chat, rotate it immediately in Google AI Studio / Groq console. History is forever.

**Important**: `.env` is in `.gitignore` and won't be committed to git.

### Step 3: Start the Server
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Expected output:**
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete
```

### Step 4: Test the API

**Health Check:**
```bash
curl http://localhost:8000/health
```

**Access API Documentation:**
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API Endpoints

### 1. Ingest Documents
```bash
curl -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "docs": [
      {
        "id": "doc1",
        "text": "RAG is a technique that combines retrieval with generation...",
        "meta": {"source": "docs", "topic": "rag"}
      }
    ]
  }'
```

### 2. Query (Synchronous)
```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is RAG?", "top_k": 5}'
```

### 3. Query (Streaming - For Real-time UI updates)
```bash
curl -X POST http://localhost:8000/query/stream \
  -H "Content-Type: application/json" \
  -d '{"query": "What is RAG?", "top_k": 5}'
```

This streams SSE events showing agent reasoning in real-time.

## Run the Demo

```bash
# In new terminal, after server is running
python demo.py
```

This demonstrates:
1. Document ingestion
2. Semantic search
3. LLM generation
4. Agent planning & execution

## Project Structure

```
Agentic RAG/
├── .env                 # API keys (git-ignored)
├── .env.example         # Template for .env (can commit)
├── requirements.txt     # Python dependencies
├── README.md           # Main documentation
├── SETUP.md            # This file
│
├── app/
│   ├── main.py         # FastAPI app with endpoints
│   ├── schemas.py      # Pydantic models
│   ├── rag/
│   │   └── store.py    # FAISS vector store
│   ├── llm/
│   │   └── gemini_client.py  # Gemini API client
│   └── agents/
│       └── planner.py  # Agentic planner & tools
│
├── examples/
│   └── client.py       # Python client for testing
│
├── demo.py            # Complete demo script
└── verify_setup.py    # Setup verification
```

## Modern RAG Techniques Showcased

### 1. **Semantic Search**
- Uses sentence-transformers embeddings with FAISS
- Efficient similarity search (O(1) query time after index build)

### 2. **Agentic Patterns**
- Agent planner decides tool use (retrieval vs generation)
- Tool interface for extensibility
- Multi-step reasoning

### 3. **Real-time Streaming (SSE)**
- Server-Sent Events for client-side real-time updates
- Similar to your NSim project
- Perfect for showing agent step-by-step reasoning

### 4. **Vector Store Persistence**
- FAISS index + JSON metadata
- Automatic persistence to disk
- Reload on server restart

### 5. **Clean Architecture**
- Modular tool interface
- Dependency injection pattern
- Easy to extend with new tools

## Deployment (Production)

### Option 1: VPS (Nginx + PM2)
```bash
# SSH into VPS
ssh user@your-vps

# Clone and setup
git clone <your-repo>
cd agentic-rag
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Create .env with production API keys
echo "GEMINI_API_KEY=xxx" > .env

# Start with PM2
pm2 start app.main:app --name "rag-api" -- uvicorn --host 0.0.0.0 --port 8000

# Setup Nginx reverse proxy
# (edit /etc/nginx/sites-available/default)
```

### Option 2: Docker (recommended)
```dockerfile
# see ./Dockerfile (non-root, no secrets baked in)
```
```bash
docker build -t agentic-rag .
docker run -p 8000:8000 --env-file .env agentic-rag
# or full stack:
docker compose up --build
```
> Never `COPY .env .env` into an image. Pass secrets at runtime via `--env-file` / compose `env_file`.

### Option 3: Cloud (Google Cloud, AWS Lambda)
- FastAPI is serverless-compatible
- Use environment variables for (GEMINI_API_KEY, etc.)
- Store FAISS index in cloud storage (GCS, S3)

## Environment Variables

| Variable | Priority | Description |
|----------|----------|-------------|
| `GEMINI_API_KEY` | **Required** | Your Gemini API key |
| `GEMINI_MODEL` | Optional | Model name (default: gemini-3.5-flash) |
| `RAG_DATA_DIR` | Optional | Where to store FAISS index (default: data/) |

## Troubleshooting

### "ModuleNotFoundError: No module named 'fastapi'"
- Make sure virtual environment is activated
- Run: `pip install -r requirements.txt`

### "404 Quota exceeded"
- Gemini API usage quota reached
- Check billing in Google Cloud Console
- Or use a different API key

### Vector Store Not Persisting
- Check `RAG_DATA_DIR` has write permissions
- Verify `data/faiss.index` and `data/meta.json` exist

### SSE Not Streaming
- Check Chrome/Firefox console for CORS errors
- Ensure `--reload` flag is used in development
- Test with: `curl -N http://localhost:8000/query/stream ...`

## Next Steps

### Level 1: Extend Tools
Add more tools to the agent planner:
- Web search tool
- Code execution sandbox
- Document parser (PDF, DOCX)

### Level 2: Multi-Agent
Implement supervisor + specialist agents:
- Supervisor delegates to specialized sub-agents
- Each agent has specific tools
- Coordinator synthesizes results

### Level 3: Advanced RAG
- Query expansion & reranking
- Long-context handling
- Memory/chat history
- Hybrid search (keyword + semantic)

### Level 4: Production Features
- Rate limiting & authentication
- Logging & monitoring
- Batch ingestion pipeline
- A/B testing for prompts

## Resources

- **FastAPI**: https://fastapi.tiangolo.com/
- **FAISS**: https://github.com/facebookresearch/faiss
- **Sentence-Transformers**: https://www.sbert.net/
- **Gemini API**: https://ai.google.dev
- **RAG Papers**: https://arxiv.org/abs/2005.11401

## Support

For issues, check:
1. `.env` file has correct API key
2. All packages installed: `pip list | grep -E "fastapi|faiss|transformers"`
3. Server is running: `curl http://localhost:8000/health`
4. Port 8000 is not in use: `netstat -tuln | grep 8000` (Linux/Mac)

---

**Created for**: Yuvraj Bhardwaj - Gen-AI Engineer  
**Date**: June 2026  
**Stack**: FastAPI + FAISS + Gemini + SSE Streaming
