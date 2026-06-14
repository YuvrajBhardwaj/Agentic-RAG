#!/bin/bash
cd "c:\Users\yuvra\OneDrive\Desktop\Agentic RAG"
.\.venv\Scripts\uvicorn app.main:app --host 0.0.0.0 --port 8000
