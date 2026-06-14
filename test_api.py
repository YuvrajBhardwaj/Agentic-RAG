import requests
import json
import time

time.sleep(3)  # Wait for server to fully start

print("\n" + "="*60)
print("TESTING AGENTIC RAG API")
print("="*60)

BASE_URL = "http://localhost:8000"

# Test 1: Health Check
print("\n[1] Health Check")
try:
    r = requests.get(f"{BASE_URL}/health", timeout=5)
    print(f"  Status: {r.status_code}")
    print(f"  Response: {r.json()}")
except Exception as e:
    print(f"  ERROR: {e}")

# Test 2: Ingest Documents
print("\n[2] Ingesting Documents")
docs = {
    "docs": [
        {
            "id": "doc1",
            "text": "FastAPI is a modern, fast web framework for building APIs with Python",
            "meta": {"source": "docs", "category": "fastapi"}
        },
        {
            "id": "doc2",
            "text": "RAG combines retrieval and generation for better AI responses",
            "meta": {"source": "docs", "category": "rag"}
        },
        {
            "id": "doc3",
            "text": "Embeddings are dense vector representations of text for similarity search",
            "meta": {"source": "docs", "category": "embeddings"}
        }
    ]
}

try:
    r = requests.post(f"{BASE_URL}/ingest", json=docs, timeout=10)
    print(f"  Status: {r.status_code}")
    print(f"  Response: {r.json()}")
except Exception as e:
    print(f"  ERROR: {e}")

# Test 3: Query (Sync)
print("\n[3] Query (Synchronous)")
query = {"query": "What is RAG?", "top_k": 2}
try:
    r = requests.post(f"{BASE_URL}/query", json=query, timeout=30)
    print(f"  Status: {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        print(f"  Answer (first 200 chars): {data['answer'][:200]}...")
        print(f"  Sources: {len(data['sources'])} documents")
    else:
        print(f"  Response: {r.text}")
except Exception as e:
    print(f"  ERROR: {e}")

# Test 4: Query (Stream)
print("\n[4] Query (Streaming via SSE)")
try:
    r = requests.post(f"{BASE_URL}/query/stream", json=query, timeout=30, stream=True)
    print(f"  Status: {r.status_code}")
    print(f"  Streaming events:")
    event_count = 0
    for line in r.iter_lines():
        if line:
            event_count += 1
            line_text = line.decode('utf-8') if isinstance(line, bytes) else line
            if event_count <= 3:  # Show first 3 events
                print(f"    {line_text[:80]}")
    print(f"  Total events streamed: {event_count}")
except Exception as e:
    print(f"  ERROR: {e}")

print("\n" + "="*60)
print("API TESTING COMPLETE")
print("="*60)
print("\nAPI Documentation: http://localhost:8000/docs")
print("ReDoc: http://localhost:8000/redoc")
