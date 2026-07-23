"""
Text-to-SQL AI pipeline (agent orchestration, SQL execution, prompt-injection
validation), re-exported so call sites can do `from app.ai import BIAgent`
instead of importing each module. Schema retrieval (RAG) and prompt
templates now live in their own top-level packages — see app.rag and
app.prompts.
"""

from app.ai.agent import BIAgent
from app.ai.sql_executor import DatasetSQLExecutor
from app.ai.validators import PromptInjectionValidator

__all__ = [
    "BIAgent",
    "DatasetSQLExecutor",
    "PromptInjectionValidator",
]
