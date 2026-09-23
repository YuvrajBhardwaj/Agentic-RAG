from pydantic import BaseModel
from typing import List, Optional, Dict, Any


class Doc(BaseModel):
    id: str
    text: str
    meta: Optional[Dict[str, Any]] = None


class IngestRequest(BaseModel):
    docs: List[Doc]
    tenant_id: Optional[str] = None


class QueryRequest(BaseModel):
    query: str
    top_k: Optional[int] = 5
    tenant_id: Optional[str] = None


class QueryResponse(BaseModel):
    answer: str
    sources: List[Dict[str, Any]]


class StoreStats(BaseModel):
    total_documents: int
    index_size: int
    sources: Dict[str, int]
