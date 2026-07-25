"""
Unstructured data connector: extracts text from PDFs and plain text
documents, then chunks it into embedding-ready segments.

This is the connector type most different from the others: there's no
schema, no rows, no columns, only raw text that has to be extracted,
cleaned, and split into chunks small enough to embed and retrieve
usefully in a RAG pipeline. Chunk size and overlap are the two decisions
that most affect retrieval quality: too large and irrelevant text dilutes
the embedding; too small and necessary context gets split across chunks.

Handles two source types: real PDF files (via pypdf) and plain text
(handling both means this connector works whether upstream unstructured
content arrives as PDFs, scanned document exports, or plain text dumps
from a CMS or wiki export).
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Optional

from pypdf import PdfReader

from .base import BaseConnector, ExtractedRecord, ExtractionResult, SourceCategory


def chunk_text(text: str, chunk_size: int = 800, overlap: int = 150) -> list[str]:
    """Splits text into overlapping chunks by character count, breaking
    on sentence boundaries where possible so chunks don't cut a sentence
    in half mid-thought, which meaningfully hurts embedding quality.

    Overlap between consecutive chunks means a fact that lands near a
    chunk boundary still appears with surrounding context in at least
    one chunk, rather than being split awkwardly across two.
    """
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []

    sentences = re.split(r"(?<=[.!?])\s+", text)

    chunks: list[str] = []
    current = ""

    for sentence in sentences:
        if len(current) + len(sentence) + 1 <= chunk_size:
            current = f"{current} {sentence}".strip()
        else:
            if current:
                chunks.append(current)
            # start the next chunk with the tail of the previous one, for overlap
            overlap_text = current[-overlap:] if len(current) > overlap else current
            current = f"{overlap_text} {sentence}".strip()

    if current:
        chunks.append(current)

    return chunks


class UnstructuredConnector(BaseConnector):
    category = SourceCategory.UNSTRUCTURED

    def __init__(self, file_paths: list[str], chunk_size: int = 800, overlap: int = 150,
                 connector_name: str = "unstructured_docs"):
        self.file_paths = file_paths
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.name = connector_name

    def _extract_text(self, file_path: str) -> str:
        path = Path(file_path)
        if path.suffix.lower() == ".pdf":
            reader = PdfReader(file_path)
            return "\n".join(page.extract_text() or "" for page in reader.pages)
        else:
            return path.read_text(encoding="utf-8", errors="replace")

    def extract(self) -> ExtractionResult:
        records = []
        errors = []

        for file_path in self.file_paths:
            try:
                raw_text = self._extract_text(file_path)
                if not raw_text.strip():
                    errors.append({"file": file_path, "error": "no_extractable_text"})
                    continue

                chunks = chunk_text(raw_text, self.chunk_size, self.overlap)
                doc_id_base = Path(file_path).stem

                for i, chunk in enumerate(chunks):
                    chunk_hash = hashlib.sha256(chunk.encode()).hexdigest()[:12]
                    records.append(ExtractedRecord(
                        source_name=self.name,
                        source_category=self.category,
                        record_id=f"{doc_id_base}_chunk_{i:04d}_{chunk_hash}",
                        payload={
                            "source_file": file_path,
                            "chunk_index": i,
                            "chunk_count": len(chunks),
                            "text": chunk,
                            "char_count": len(chunk),
                        },
                        content_type="unstructured",
                    ))

            except Exception as e:
                errors.append({"file": file_path, "error": str(e)})

        return ExtractionResult(records=records, errors=errors, source_name=self.name)
