from typing import Dict, Any
from backend.rag.retriever import retriever

async def search_docs(query: str, document_filter: str = "all") -> Dict[str, Any]:
    """
    Retrieves policy rules, schedules, comfort bands, and maintenance notes from docs/.
    Fulfills Problem 1B & 2.2: RAG over governing operational documents.
    """
    chunks = retriever.search(query=query, doc_filter=document_filter, top_k=3)
    return {
        "query": query,
        "results_found": len(chunks),
        "chunks": chunks
    }
