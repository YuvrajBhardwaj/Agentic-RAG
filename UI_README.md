# UI Guide - Agentic RAG

## Quick Start - HTML UI

### 1. Open the UI
Simply open `index.html` in your browser:
```bash
# Just open the file directly
open index.html

# Or start a simple HTTP server
python -m http.server 8080
# Then visit: http://localhost:8080
```

### 2. Features

**📚 Document Ingestion Panel (Left)**
- Add documents to the vector store
- Specify document ID, text content, and metadata
- Documents persist to disk via FAISS
- Track total documents ingested

**💬 Query Panel (Right)**
- Ask questions about your documents
- Two query modes:
  - **Sync**: Get full answer at once
  - **Stream**: Watch agent reasoning in real-time (SSE)
- Real-time events showing:
  - `plan_start` - Agent initialized
  - `step` - Tool execution (retrieval, generation)
  - `plan_complete` - Agent finished

### 3. Example Workflow

```
1. Ingest Documents:
   - ID: "ai-101"
   - Text: "AI is transforming industries..."
   - Meta: {"source": "docs", "topic": "ai"}

2. Query:
   - Ask: "What impact does AI have?"
   - Stream the response to see agent thinking
```

## Next: Upgrade to Next.js Frontend

For a production-grade UI with:
- TypeScript support
- Better performance
- Server-side rendering
- Authentication ready
- Deployment to Vercel

See `NEXT_JS_SETUP.md` (coming next)

## Troubleshooting

### "Cannot connect to API"
- Make sure FastAPI server is running on port 8000
- Check: `http://localhost:8000/health`

### CORS Issues
- Already handled! The HTML UI uses `http://localhost:8000` directly
- For production, configure CORS in `app/main.py`

### Streaming Not Working
- Check browser console (F12)
- Verify EventSource support in your browser
- FastAPI SSE endpoint: `/query/stream`

## Files

- `index.html` - Standalone HTML/JS UI
- `NEXT_JS_SETUP.md` - Instructions for React/Next.js frontend
- `examples/client.py` - Python client for programmatic access
