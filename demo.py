"""
Complete Agentic RAG Demo
Demonstrates all features: ingestion, retrieval, generation, SSE streaming
"""

from app.rag.store import VectorStore
from app.llm.gemini_client import generate
from app.agents.planner import AgentPlanner, RetrievalTool, GenerationTool
import os

# Initialize components
print("=" * 60)
print("AGENTIC RAG DEMO")
print("=" * 60)

print("\n[1] Initializing Vector Store...")
store = VectorStore(persist_dir="demo_data")

print("[2] Ingesting sample documents...")
sample_docs = [
    {
        "id": "rag-101",
        "text": "RAG (Retrieval-Augmented Generation) combines document retrieval with LLM generation. It retrieves relevant documents and uses them as context for generating accurate, grounded responses.",
        "meta": {"source": "docs", "topic": "rag", "difficulty": "beginner"}
    },
    {
        "id": "rag-102", 
        "text": "RAG improves LLM accuracy by providing factual context. This reduces hallucination and ensures responses are grounded in real data from your knowledge base.",
        "meta": {"source": "docs", "topic": "rag", "difficulty": "beginner"}
    },
    {
        "id": "embeddings-101",
        "text": "Embeddings convert text to dense vectors. Models like sentence-transformers create semantic representations that enable similarity search. FAISS provides efficient nearest-neighbor search.",
        "meta": {"source": "docs", "topic": "embeddings", "difficulty": "intermediate"}
    },
    {
        "id": "agents-101",
        "text": "Agentic systems use planning, tool use, and reasoning. An agent planner decides which tools to use, executes them in sequence, and synthesizes results into coherent responses.",
        "meta": {"source": "docs", "topic": "agents", "difficulty": "advanced"}
    }
]

store.add_documents(sample_docs)
print(f"   Ingested {len(sample_docs)} documents")

print("\n[3] Vector Search Test...")
query = "What is RAG and why is it important?"
results = store.similarity_search(query, k=2)
print(f"   Query: '{query}'")
print(f"   Top results: {len(results)}")
for i, r in enumerate(results, 1):
    print(f"   {i}. {r['id']}: {r['text'][:100]}...")

print("\n[4] LLM Generation Test...")
prompt = f"Based on this context: {results[0]['text'][:200]}\n\nExplain RAG briefly."
response = generate(prompt)
print(f"   Model: {os.environ.get('GEMINI_MODEL')}")
if "[ERROR" not in response:
    print(f"   Response: {response[:200]}...")
else:
    print(f"   Status: {response[:100]}")

print("\n[5] Agent Planner Test...")
planner = AgentPlanner([
    RetrievalTool(store),
    GenerationTool(generate)
])

plan = planner.plan("What is the relationship between embeddings and RAG?")
print(f"   Goal: {plan.goal}")
print(f"   Steps: {len(plan.steps)}")
for i, step in enumerate(plan.steps, 1):
    print(f"   {i}. {step['tool']} - {step['rationale']}")

print("\n[6] Executing Agent Plan...")
print("   Plan execution streaming:")
for result in planner.execute_plan(plan):
    if result.strip():
        print(f"     {result.strip()[:80]}")

print("\n" + "=" * 60)
print("DEMO COMPLETE")
print("=" * 60)
print("\nTo start the API server:")
print("  uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload")
print("\nOr run the client:")
print("  python examples/client.py --query 'Your question here'")
