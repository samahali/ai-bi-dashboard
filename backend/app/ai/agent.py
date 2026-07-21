"""
AI Agent — orchestrates the full Text-to-SQL pipeline using LangChain.

Supports IBM Granite (Watsonx) as primary LLM and OpenAI as fallback. Both
providers are wrapped as LangChain `Runnable`s (a custom `LLM` subclass for
Watsonx — see langchain_llms.py — and `ChatOpenAI` for OpenAI) and driven
through one `prompt | llm | StrOutputParser()` chain, so SQL generation
itself is genuinely LangChain-orchestrated rather than a raw SDK call
branching on provider at the call site.
"""
import time
from typing import Any

import structlog

from app.config import settings
from app.core.exceptions import AIServiceError, PromptInjectionError
from app.db.models import Dataset

logger = structlog.get_logger(__name__)


class BIAgent:
    """
    Business Intelligence AI Agent.

    Responsibilities:
    1. Validate user question (prompt injection prevention)
    2. Build dataset context (schema + samples)
    3. Generate SQL via LLM
    4. Execute SQL against the dataset
    5. Return structured results with metadata
    """

    def __init__(self, provider: str | None = None) -> None:
        self.provider = provider or settings.default_llm_provider
        self.llm = self._init_llm()

    def _init_llm(self):
        if self.provider == "granite":
            return self._init_granite()
        elif self.provider == "openai":
            return self._init_openai()
        raise AIServiceError(f"Unknown LLM provider: {self.provider}")

    def _init_granite(self):
        try:
            from ibm_watsonx_ai.foundation_models import Model
            from ibm_watsonx_ai.metanames import GenTextParamsMetaNames as Params

            from app.ai.langchain_llms import WatsonxGraniteLLM

            watsonx_model = Model(
                model_id=settings.watsonx_model_id,
                credentials={
                    "apikey": settings.watsonx_apikey,
                    "url": settings.watsonx_url,
                },
                project_id=settings.watsonx_project_id,
                params={
                    Params.MAX_NEW_TOKENS: 512,
                    Params.TEMPERATURE: 0.0,   # Deterministic for SQL
                    Params.STOP_SEQUENCES: [";"],
                },
            )
            return WatsonxGraniteLLM(model=watsonx_model)
        except Exception as e:
            if not settings.openai_api_key or settings.openai_api_key.startswith("sk-your-"):
                raise AIServiceError(
                    f"Granite (Watsonx) initialization failed and no valid OpenAI "
                    f"fallback key is configured. Original error: {e}"
                ) from e
            logger.warning("Granite init failed, falling back to OpenAI", error=str(e))
            self.provider = "openai"
            return self._init_openai()

    def _init_openai(self):
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=settings.openai_model,
            api_key=settings.openai_api_key,
            temperature=0,
            max_tokens=512,
        )

    async def process_question(
        self,
        question: str,
        dataset: Dataset,
    ) -> dict[str, Any]:
        """
        Main entry point. Returns:
        {
            sql: str,
            results: list[dict],
            confidence_score: float,
            visualization_suggestion: str,
        }
        """
        # 1. Validate input
        from app.ai.validators import PromptInjectionValidator
        is_valid, reason = PromptInjectionValidator.validate(question)
        if not is_valid:
            raise PromptInjectionError(reason)

        # 2. Build schema context — RAG: retrieve only the columns relevant
        # to this question instead of always dumping the full schema. Falls
        # back to the full schema if ChromaDB is unavailable or the dataset
        # is small enough that retrieval wouldn't narrow anything down.
        from app.ai.rag_store import SchemaRAGStore
        all_columns_metadata = dataset.columns_metadata or {}
        relevant_columns = SchemaRAGStore().retrieve_relevant_columns(dataset.id, question)
        if relevant_columns:
            columns_metadata = {
                col: meta for col, meta in all_columns_metadata.items() if col in relevant_columns
            }
        else:
            columns_metadata = all_columns_metadata
        schema_str = self._format_schema(columns_metadata)

        # 3. Generate SQL
        sql = await self._generate_sql(question, schema_str, dataset.name)
        logger.info("SQL generated", dataset_id=dataset.id, sql=sql)

        # 4. Execute SQL against dataset file
        from app.ai.sql_executor import DatasetSQLExecutor
        executor = DatasetSQLExecutor()
        results = executor.execute(sql, dataset.file_path, dataset.file_type)

        # 5. Suggest visualization type
        viz_suggestion = self._suggest_visualization(results)

        return {
            "sql": sql,
            "results": results[:500],     # Cap results for response size
            "confidence_score": 0.90,
            "visualization_suggestion": viz_suggestion,
        }

    async def _generate_sql(self, question: str, schema: str, table_name: str) -> str:
        from langchain_core.output_parsers import StrOutputParser
        from langchain_core.prompts import PromptTemplate

        from app.ai.prompts import build_text_to_sql_prompt

        # A single LangChain Runnable chain regardless of provider — the
        # prompt template just passes through the already-built prompt
        # string (build_text_to_sql_prompt does the actual templating so
        # the RAG-filtered schema and few-shot examples stay identical to
        # before), then the chosen LLM, then a plain string parser.
        chain = (
            PromptTemplate.from_template("{prompt}")
            | self.llm
            | StrOutputParser()
        )

        prompt = build_text_to_sql_prompt(
            question=question,
            schema=schema,
            table_name=table_name,
        )
        raw_sql = await chain.ainvoke({"prompt": prompt})
        return self._clean_sql(raw_sql)

    @staticmethod
    def _clean_sql(raw: str) -> str:
        """Strip markdown code fences and whitespace from LLM output."""
        sql = raw.strip()
        for fence in ("```sql", "```"):
            if sql.startswith(fence):
                sql = sql[len(fence):]
        if sql.endswith("```"):
            sql = sql[:-3]
        # Ensure it ends with semicolon
        sql = sql.strip().rstrip(";") + ";"
        return sql

    @staticmethod
    def _format_schema(columns_metadata: dict) -> str:
        lines = []
        for col, meta in columns_metadata.items():
            col_type = meta.get("type", "string").upper()
            nullable = "" if meta.get("nullable") else " NOT NULL"
            # Always show columns pre-quoted so the model mirrors this exact
            # form everywhere it references them (SELECT, WHERE, GROUP BY, ...) —
            # column names with spaces/special chars otherwise get inconsistently
            # quoted (e.g. quoted in GROUP BY but bare in SELECT, breaking the parser).
            lines.append(f'  "{col}"  {col_type}{nullable}')
        return "\n".join(lines)

    @staticmethod
    def _suggest_visualization(results: list[dict]) -> str:
        if not results:
            return "table"
        import pandas as pd
        df = pd.DataFrame(results)
        cols = list(df.columns)
        numeric_cols = [c for c in cols if pd.api.types.is_numeric_dtype(df[c])]

        if len(cols) == 2 and len(numeric_cols) == 1:
            if any(kw in cols[0].lower() for kw in ["date", "month", "year", "time", "week"]):
                return "line"
            if len(df) <= 8:
                return "pie"
            return "bar"
        if len(numeric_cols) >= 2:
            return "scatter"
        return "bar"
