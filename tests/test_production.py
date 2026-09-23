"""Production smoke tests — no model download, no live server.

Run:  pytest -q
"""
import os
import sys
import types

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ── Stub heavy third-party deps so tests run without torch/faiss ──
if "faiss" not in sys.modules:
    try:
        import faiss  # noqa: F401
    except Exception:
        fake_faiss = types.ModuleType("faiss")

        class FakeIndex:
            ntotal = 0

            def add(self, *a, **k):
                pass

        fake_faiss.IndexFlatL2 = lambda dim: FakeIndex()
        fake_faiss.read_index = lambda p: FakeIndex()
        fake_faiss.write_index = lambda *a, **k: None
        sys.modules["faiss"] = fake_faiss

if "sentence_transformers" not in sys.modules:
    try:
        import sentence_transformers  # noqa: F401
    except Exception:
        fake_st = types.ModuleType("sentence_transformers")

        class FakeModel:
            def get_embedding_dimension(self):
                return 384

            def encode(self, *a, **k):
                import numpy as np
                texts = a[0] if a else [""]
                return np.zeros((len(texts), 384), dtype="float32")

        fake_st.SentenceTransformer = lambda *a, **k: FakeModel()
        sys.modules["sentence_transformers"] = fake_st

for _mod in ["groq"]:
    if _mod not in sys.modules:
        try:
            __import__(_mod)
        except Exception:
            _m = types.ModuleType(_mod)

            class _DummyGroq:
                def __init__(self, *a, **k):
                    pass

            _m.Groq = _DummyGroq
            sys.modules[_mod] = _m

for _mod in ["google", "google.genai"]:
    if _mod not in sys.modules:
        try:
            __import__(_mod)
        except Exception:
            sys.modules[_mod] = types.ModuleType(_mod)

from fastapi.testclient import TestClient


def _load_app(monkeypatch, tmp_path, api_key="test-key-123"):
    monkeypatch.setenv("RAG_API_KEY", api_key)
    monkeypatch.setenv("RAG_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("RATE_LIMIT_PER_MIN", "1000")
    # Fresh import per test run
    for mod in list(sys.modules):
        if mod == "app.main" or mod.startswith("app.main."):
            del sys.modules[mod]
    import app.main as main
    return main


def test_health_open_without_key(tmp_path, monkeypatch):
    main = _load_app(monkeypatch, tmp_path, api_key="")
    main.API_KEY = ""
    c = TestClient(main.app)
    r = c.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "healthy"


def test_protected_routes_reject_without_key(tmp_path, monkeypatch):
    main = _load_app(monkeypatch, tmp_path, api_key="secret-xyz")
    c = TestClient(main.app)
    assert c.get("/store-stats").status_code == 401
    assert c.post("/query", json={"query": "hi"}).status_code == 401


def test_protected_routes_accept_with_key(tmp_path, monkeypatch):
    main = _load_app(monkeypatch, tmp_path, api_key="secret-xyz")
    c = TestClient(main.app, headers={"X-API-Key": "secret-xyz"})
    r = c.get("/store-stats")
    assert r.status_code == 200, r.text
    assert "total_documents" in r.json()


def test_tenant_isolation(tmp_path, monkeypatch):
    main = _load_app(monkeypatch, tmp_path, api_key="")
    main.API_KEY = ""
    t = main.sanitize_tenant("../../etc")
    assert "/" not in t and ".." not in t and "etc" in t
    assert main.sanitize_tenant("") == "default"
    a = main.get_store("client-a")
    b = main.get_store("client-b")
    assert a is not b
    assert "client-a" in a.persist_dir and "client-b" in b.persist_dir


def test_chunk_ingest_splits_vectors(tmp_path, monkeypatch):
    """Regression test for the whole-PDF-as-1-vector bug."""
    main = _load_app(monkeypatch, tmp_path, api_key="")
    main.API_KEY = ""

    class FakeStore:
        def __init__(self):
            self.docs = []

        def add_documents(self, docs):
            self.docs.extend(docs)

    store = FakeStore()
    long_text = "word " * 3000  # >> CHUNK_SIZE so must split
    parent_id, n = main.ingest_text_as_chunks(store, long_text, "sample.pdf", 3)
    assert n > 1, "chunking must produce multiple vectors"
    assert len(store.docs) == n
    assert all(d["meta"]["parent_id"] == parent_id for d in store.docs)
    assert store.docs[0]["meta"]["chunk_index"] == 0
