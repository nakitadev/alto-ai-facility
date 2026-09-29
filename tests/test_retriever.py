"""
Unit tests for backend/rag/retriever.py.
Verifies RAG document indexing, markdown parsing, keyword searching, and doc filters.
"""

from backend.rag.retriever import retriever

def test_retriever_indexed_documents():
    assert len(retriever.chunks) > 0
    # Ensure all required docs are loaded
    sources = set(c.doc_name for c in retriever.chunks)
    assert "ai_control_policy.md" in sources
    assert "building_schedule.md" in sources
    assert "maintenance_log.md" in sources
    assert "operator_manual.md" in sources

def test_search_docs_general_query():
    results = retriever.search("comfort band temperature office hours", top_k=3)
    assert len(results) > 0
    assert any("comfort" in r["content"].lower() or "temperature" in r["content"].lower() for r in results)

def test_search_docs_with_filter():
    results = retriever.search("schedule hours", doc_filter="building_schedule.md", top_k=3)
    assert len(results) > 0
    for r in results:
        assert r["source_doc"] == "building_schedule.md"

def test_search_docs_policy_occupancy_rule():
    results = retriever.search("AC-S3 occupancy shutdown", doc_filter="ai_control_policy.md", top_k=3)
    assert len(results) > 0
    assert any("ai_control_policy.md" in r["source_doc"] for r in results)
