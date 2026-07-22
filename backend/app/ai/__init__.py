"""
Text-to-SQL / RAG pipeline (schema retrieval, prompting, generation, safe
execution), re-exported so call sites can do `from app.ai import BIAgent`
instead of importing each module.
"""

from app.ai.agent import BIAgent
from app.ai.rag_store import SchemaRAGStore
from app.ai.sql_executor import DatasetSQLExecutor
from app.ai.validators import PromptInjectionValidator

__all__ = [
    "BIAgent",
    "SchemaRAGStore",
    "DatasetSQLExecutor",
    "PromptInjectionValidator",
]
