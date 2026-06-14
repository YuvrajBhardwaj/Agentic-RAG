#!/usr/bin/env python
"""Test script to verify Agentic RAG setup"""

import sys
import os

print("[1] Checking Python environment...")
print(f"    Python: {sys.version}")
print(f"    Directory: {os.getcwd()}")

print("\n[2] Checking .env file...")
from dotenv import load_dotenv
load_dotenv()
api_key = os.environ.get("GEMINI_API_KEY")
model = os.environ.get("GEMINI_MODEL")
print(f"    API Key configured: {bool(api_key)}")
print(f"    Model: {model}")

print("\n[3] Checking imports...")
try:
    from fastapi import FastAPI
    print("    FastAPI: OK")
except ImportError as e:
    print(f"    FastAPI: FAILED - {e}")
    sys.exit(1)

try:
    from sentence_transformers import SentenceTransformer
    print("    SentenceTransformers: OK")
except ImportError as e:
    print(f"    SentenceTransformers: FAILED - {e}")
    sys.exit(1)

try:
    import faiss
    print("    FAISS: OK")
except ImportError as e:
    print(f"    FAISS: FAILED - {e}")
    sys.exit(1)

try:
    import google.generativeai as genai
    print("    Google Generative AI: OK")
except ImportError as e:
    print(f"    Google Generative AI: FAILED - {e}")
    sys.exit(1)

print("\n[4] Testing app import...")
try:
    from app.main import app, store, planner
    print("    App: OK")
    print("    Store: OK")
    print("    Planner: OK")
except ImportError as e:
    print(f"    App import failed: {e}")
    sys.exit(1)

print("\n[5] Checking FastAPI routes...")
print(f"    Total routes: {len(app.routes)}")
for route in app.routes:
    if hasattr(route, 'path'):
        print(f"      {route.methods if hasattr(route, 'methods') else 'N/A'} {route.path}")

print("\n[SUCCESS] Setup verification complete!")
print("\nTo start the server, run:")
print("  .venv\\Scripts\\uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload")
print("\nThen test with:")
print("  curl http://localhost:8000/health")
print("  curl -X POST http://localhost:8000/ingest -H 'Content-Type: application/json' ...")
