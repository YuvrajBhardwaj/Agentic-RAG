import os
import json
import faiss
import numpy as np
from typing import List, Dict, Any, Optional
from sentence_transformers import SentenceTransformer


EMB_MODEL = os.environ.get("EMBEDDING_MODEL", "all-MiniLM-L6-v2")


class VectorStore:
    def __init__(self, persist_dir: str = "data"):
        self.persist_dir = persist_dir
        os.makedirs(self.persist_dir, exist_ok=True)
        self.model = SentenceTransformer(EMB_MODEL)
        self.index_file = os.path.join(self.persist_dir, "faiss.index")
        self.meta_file = os.path.join(self.persist_dir, "meta.json")

        self.dim = self.model.get_embedding_dimension()
        self.index: Optional[faiss.IndexFlatL2] = None
        self.metadatas: List[Dict[str, Any]] = []
        self._load()

    def _load(self):
        if os.path.exists(self.index_file) and os.path.exists(self.meta_file):
            try:
                self.index = faiss.read_index(self.index_file)
                with open(self.meta_file, "r", encoding="utf-8") as f:
                    self.metadatas = json.load(f)
            except Exception:
                self.index = faiss.IndexFlatL2(self.dim)
                self.metadatas = []
        else:
            self.index = faiss.IndexFlatL2(self.dim)
            self.metadatas = []

    def _save(self):
        faiss.write_index(self.index, self.index_file)
        with open(self.meta_file, "w", encoding="utf-8") as f:
            json.dump(self.metadatas, f, ensure_ascii=False, indent=2)

    def add_documents(self, docs: List[Dict[str, Any]]):
        texts = [d["text"] for d in docs]
        ids = [d.get("id") for d in docs]
        metas = [d.get("meta", {}) for d in docs]
        embs = self.model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
        if embs.ndim == 1:
            embs = np.expand_dims(embs, axis=0)
        self.index.add(embs.astype('float32'))
        for i, mid in enumerate(ids):
            self.metadatas.append({"id": mid, "text": texts[i], "meta": metas[i]})
        self._save()

    def similarity_search(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        if self.index.ntotal == 0 or not self.metadatas:
            return []
        q_emb = self.model.encode([query], convert_to_numpy=True)
        D, I = self.index.search(q_emb.astype('float32'), k)
        results = []
        for idx in I[0]:
            if 0 <= idx < len(self.metadatas):
                results.append(self.metadatas[idx])
        return results
