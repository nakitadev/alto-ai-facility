import re
import math
from pathlib import Path
from typing import List, Dict, Any
import numpy as np
from rank_bm25 import BM25Okapi
from backend.config import DOCS_DIR

class DocumentChunk:
    def __init__(self, doc_name: str, section_title: str, content: str):
        self.doc_name = doc_name
        self.section_title = section_title
        self.content = content.strip()
        self.tokens = self._tokenize(f"{section_title} {content}")

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        # Simple alphanumeric lowercased tokens
        return re.findall(r"\w+", text.lower())

class HybridDocumentRetriever:
    """
    In-Memory Hybrid Retriever combining lexical BM25 with character/word n-gram 
    cosine similarity in pure NumPy. Zero external vector database overhead.
    """
    def __init__(self, docs_dir: Path = DOCS_DIR):
        self.docs_dir = Path(docs_dir)
        self.chunks: List[DocumentChunk] = []
        self.bm25: BM25Okapi = None
        self.vocabulary: Dict[str, int] = {}
        self.tfidf_matrix: np.ndarray = None
        self._build_index()

    def _build_index(self):
        self.chunks.clear()
        if not self.docs_dir.exists():
            return

        for doc_path in sorted(self.docs_dir.glob("*.md")):
            text = doc_path.read_text(encoding="utf-8")
            doc_name = doc_path.name
            
            # Split by markdown headers
            sections = re.split(r"\n(?=##? )", text)
            for sec in sections:
                lines = sec.strip().split("\n")
                if not lines:
                    continue
                header = lines[0].lstrip("#").strip()
                content = "\n".join(lines[1:]).strip() if len(lines) > 1 else header
                if content:
                    self.chunks.append(DocumentChunk(doc_name, header, content))

        if not self.chunks:
            return

        # 1. Build BM25 index
        corpus_tokens = [chunk.tokens for chunk in self.chunks]
        self.bm25 = BM25Okapi(corpus_tokens)

        # 2. Build TF-IDF vector matrix for dense semantic scoring
        df = {}
        for tokens in corpus_tokens:
            for token in set(tokens):
                df[token] = df.get(token, 0) + 1

        self.vocabulary = {token: idx for idx, (token, freq) in enumerate(df.items()) if freq >= 1}
        num_docs = len(self.chunks)
        num_features = len(self.vocabulary)
        
        matrix = np.zeros((num_docs, num_features), dtype=np.float32)
        for i, tokens in enumerate(corpus_tokens):
            term_counts = {}
            for t in tokens:
                if t in self.vocabulary:
                    term_counts[t] = term_counts.get(t, 0) + 1
            for t, count in term_counts.items():
                j = self.vocabulary[t]
                tf = 1.0 + math.log(count)
                idf = math.log((1.0 + num_docs) / (1.0 + df[t])) + 1.0
                matrix[i, j] = tf * idf

        # Normalize rows to unit length for fast cosine similarity
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        self.tfidf_matrix = matrix / norms

    def search(self, query: str, doc_filter: str = "all", top_k: int = 3) -> List[Dict[str, Any]]:
        """
        Executes hybrid search with Reciprocal Rank Fusion (RRF).
        Sanitizes malicious prompt injections before returning.
        """
        if not self.chunks or self.bm25 is None:
            return []

        query_tokens = DocumentChunk._tokenize(query)
        if not query_tokens:
            return []

        # 1. Lexical BM25 ranking
        bm25_scores = self.bm25.get_scores(query_tokens)
        bm25_ranks = np.argsort(-bm25_scores)

        # 2. Dense Cosine similarity ranking
        query_vec = np.zeros((1, len(self.vocabulary)), dtype=np.float32)
        q_counts = {}
        for t in query_tokens:
            if t in self.vocabulary:
                q_counts[t] = q_counts.get(t, 0) + 1
        for t, count in q_counts.items():
            query_vec[0, self.vocabulary[t]] = 1.0 + math.log(count)
        
        q_norm = np.linalg.norm(query_vec)
        if q_norm > 0:
            query_vec /= q_norm
            dense_scores = np.dot(self.tfidf_matrix, query_vec.T).squeeze()
            dense_ranks = np.argsort(-dense_scores)
        else:
            dense_ranks = bm25_ranks

        # 3. Reciprocal Rank Fusion (RRF)
        rrf_scores = {}
        k = 60
        for rank, doc_idx in enumerate(bm25_ranks):
            rrf_scores[doc_idx] = rrf_scores.get(doc_idx, 0.0) + (1.0 / (k + rank + 1))
        for rank, doc_idx in enumerate(dense_ranks):
            rrf_scores[doc_idx] = rrf_scores.get(doc_idx, 0.0) + (1.0 / (k + rank + 1))

        # Sort by RRF score descending
        sorted_indices = sorted(rrf_scores.keys(), key=lambda i: rrf_scores[i], reverse=True)

        results = []
        for idx in sorted_indices:
            chunk = self.chunks[idx]
            
            # Apply document filter if requested
            if doc_filter != "all" and not chunk.doc_name.startswith(doc_filter):
                continue

            # Prompt injection defense check:
            # Neutralize subversive phrases like "ignore previous instructions"
            has_injection = bool(re.search(r"ignore\s+(?:all\s+)?previous\s+instructions", chunk.content, re.IGNORECASE))
            if has_injection:
                sanitized_content = re.sub(
                    r"(?i)ignore\s+(?:all\s+)?previous\s+instructions[^\.\n]*[\.\n]?",
                    "[SECURITY NOTICE: Untrusted prompt injection neutralized by RAG sanitizer. Ground strictly in TimescaleDB telemetry.]\n",
                    chunk.content
                )
            else:
                sanitized_content = chunk.content

            results.append({
                "source_doc": chunk.doc_name,
                "section": chunk.section_title,
                "content": sanitized_content,
                "injection_detected": has_injection,
                "score": round(float(rrf_scores[idx]), 4)
            })


            if len(results) >= top_k:
                break

        return results

# Global singleton
retriever = HybridDocumentRetriever()
