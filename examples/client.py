#!/usr/bin/env python3
"""
Example client demonstrating Agentic RAG usage.

Usage:
  python examples/client.py --ingest
  python examples/client.py --query "What is RAG?"
  python examples/client.py --stream-query "What is RAG?"
"""

import requests
import sys
import argparse
import json
from typing import Generator


BASE_URL = "http://localhost:8000"


def ingest_documents():
    """Ingest sample documents."""
    docs = [
        {
            "id": "rag-intro",
            "text": "RAG stands for Retrieval-Augmented Generation. It combines document retrieval with LLM generation to provide answers grounded in real data.",
            "meta": {"source": "docs", "topic": "rag"}
        },
        {
            "id": "rag-benefits",
            "text": "RAG improves LLM accuracy by retrieving relevant documents and providing them as context. This reduces hallucination and improves factual correctness.",
            "meta": {"source": "docs", "topic": "rag"}
        },
        {
            "id": "vector-search",
            "text": "Vector search converts text to embeddings using neural models like sentence-transformers. FAISS is a fast library for similarity search in high-dimensional spaces.",
            "meta": {"source": "docs", "topic": "embeddings"}
        },
        {
            "id": "agents",
            "text": "Agents are AI systems that plan, use tools, and reason over multiple steps. They can retrieve information, generate responses, and delegate tasks to sub-agents.",
            "meta": {"source": "docs", "topic": "agents"}
        }
    ]
    
    resp = requests.post(f"{BASE_URL}/ingest", json={"docs": docs})
    print(f"✓ Ingested {resp.json()['ingested']} documents")


def query_synchronous(query_text: str):
    """Synchronous query."""
    resp = requests.post(f"{BASE_URL}/query", json={"query": query_text, "top_k": 3})
    data = resp.json()
    print(f"\n📝 Answer:\n{data['answer']}\n")
    print(f"📚 Sources ({len(data['sources'])}):")
    for src in data['sources']:
        print(f"  - {src['id']}: {src.get('meta', {})}")


def query_streaming(query_text: str):
    """Streaming query with SSE."""
    print(f"\n🔄 Streaming response for: {query_text}\n")
    
    resp = requests.post(
        f"{BASE_URL}/query/stream",
        json={"query": query_text, "top_k": 3},
        stream=True
    )
    
    for line in resp.iter_lines():
        if line:
            line = line.decode('utf-8')
            if line.startswith("data: "):
                try:
                    event_text = line[6:]  # Remove "data: "
                    # Parse as JSON-like string (note: may not be valid JSON due to escaping)
                    print(f"  {event_text}")
                except Exception as e:
                    print(f"  Parse error: {e}")


def main():
    parser = argparse.ArgumentParser(description="Agentic RAG client")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--ingest", action="store_true", help="Ingest sample documents")
    group.add_argument("--query", type=str, help="Synchronous query")
    group.add_argument("--stream-query", type=str, help="Streaming query with SSE")
    
    args = parser.parse_args()
    
    try:
        if args.ingest:
            ingest_documents()
        elif args.query:
            query_synchronous(args.query)
        elif args.stream_query:
            query_streaming(args.stream_query)
    except requests.exceptions.ConnectionError:
        print(f"❌ Could not connect to {BASE_URL}")
        print("   Make sure the server is running: uvicorn app.main:app --reload")
        sys.exit(1)


if __name__ == "__main__":
    main()
