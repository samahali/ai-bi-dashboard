"""
Schema RAG (retrieval-augmented generation) store, re-exported so call sites
can do `from app.rag import SchemaRAGStore` instead of importing the module.
"""

from app.rag.schema_store import SchemaRAGStore

__all__ = [
    "SchemaRAGStore",
]
