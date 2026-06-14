import os
import re
import tempfile
from typing import List, Tuple, Optional

try:
    import PyPDF2
    HAS_PYPDF = True
except ImportError:
    HAS_PYPDF = False

CHUNK_SIZE = 1000  
CHUNK_OVERLAP = 200


def extract_text_from_pdf(file_path: str, max_pages: int = None) -> Tuple[str, int]:
    if not HAS_PYPDF:
        raise ImportError("PyPDF2 not installed. Run: pip install PyPDF2")

    text = ""
    page_count = 0

    with open(file_path, 'rb') as file:
        pdf_reader = PyPDF2.PdfReader(file)
        page_count = len(pdf_reader.pages)
        for i, page in enumerate(pdf_reader.pages):
            if max_pages and i >= max_pages:
                break
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"

    return text.strip(), page_count


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    if not text:
        return []
    text = re.sub(r'\s+', ' ', text).strip()
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        if end >= len(text):
            chunks.append(text[start:].strip())
            break
        split_pos = text.rfind(' ', start, end)
        if split_pos > start:
            end = split_pos
        chunks.append(text[start:end].strip())
        start = end - overlap if end - overlap > start else end
    return [c for c in chunks if c]


def batch_process_pdfs(file_paths: List[str]) -> List[dict]:
    results = []
    for file_path in file_paths:
        try:
            filename = os.path.basename(file_path)
            text, pages = extract_text_from_pdf(file_path)
            chunks = chunk_text(text) if text else []
            size_bytes = os.path.getsize(file_path)
            results.append({
                "filename": filename,
                "text": text,
                "pages": pages,
                "chunks": len(chunks),
                "size_bytes": size_bytes,
                "status": "success",
                "error": None
            })
        except Exception as e:
            results.append({
                "filename": os.path.basename(file_path),
                "text": "",
                "pages": 0,
                "chunks": 0,
                "size_bytes": 0,
                "status": "error",
                "error": str(e)
            })
    return results
