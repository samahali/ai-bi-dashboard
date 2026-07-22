"""
AI Agent — orchestrates the full Text-to-SQL pipeline using LangChain.

Supports IBM Granite (Watsonx) as primary LLM and OpenAI as fallback. Both
providers are wrapped as LangChain `Runnable`s (a custom `LLM` subclass for
Watsonx — see langchain_llms.py — and `ChatOpenAI` for OpenAI) and driven
through one `prompt | llm | StrOutputParser()` chain, so SQL generation
itself is genuinely LangChain-orchestrated rather than a raw SDK call
branching on provider at the call site.
"""
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
        # Set True in _init_granite's except block if Granite init failed and
        # we fell back to OpenAI. Used to compute a real confidence_score
        # instead of a hardcoded constant — see process_question.
        self.used_fallback = False
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
            self.used_fallback = True
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

        # 2. Build the multi-table schema context. A dataset may contain
        # several tables (Excel sheets). `effective_tables_metadata` returns a
        # uniform {table: {columns: {...}}} view, synthesizing a single "data"
        # table for CSV/JSON and pre-multi-table datasets. RAG column filtering
        # is applied per table (Phase 1 makes retrieval itself table-aware; for
        # now it uses the primary table's columns as before).
        from app.ai.rag_store import SchemaRAGStore
        from app.utils.dataset_tables import effective_tables_metadata

        tables = effective_tables_metadata(dataset.tables_metadata, dataset.columns_metadata)
        relevant_columns = SchemaRAGStore().retrieve_relevant_columns(dataset.id, question)
        tables_schema = self._format_tables_schema(tables, relevant_columns)

        # 3. Generate SQL
        sql = await self._generate_sql(question, tables_schema)
        logger.info("SQL generated", dataset_id=dataset.id, sql=sql)

        # 3a. NO_ANSWER: the model signals it can't answer from the available
        # schema (rather than hallucinating a query). Surface it cleanly.
        no_answer = self._parse_no_answer(sql)
        if no_answer is not None:
            return {
                "sql": None,
                "results": [],
                "confidence_score": 0.0,
                "visualization_suggestion": "table",
                "no_answer": no_answer,
            }

        # 4. Execute SQL against the dataset's tables, scoped to the known
        # table names so a hallucinated/injected table is rejected.
        from app.ai.sql_executor import DatasetSQLExecutor
        executor = DatasetSQLExecutor()
        results = executor.execute(
            sql, dataset.file_path, dataset.file_type, known_tables=list(tables.keys())
        )

        # 5. Suggest visualization type
        viz_suggestion = self._suggest_visualization(results)

        # 6. Confidence score — a heuristic label for the UI, not a
        # calibrated ML confidence. 1.0: SQL generated on the primary
        # provider (no fallback) and executed without error (we only get
        # here if executor.execute() above didn't raise). 0.75: generation
        # succeeded but only after falling back from Granite to OpenAI —
        # still executed cleanly, but on the secondary provider.
        confidence_score = 0.75 if self.used_fallback else 1.0

        return {
            "sql": sql,
            "results": results[:500],     # Cap results for response size
            "confidence_score": confidence_score,
            "visualization_suggestion": viz_suggestion,
        }

    async def _generate_sql(self, question: str, tables_schema: str) -> str:
        from langchain_core.output_parsers import StrOutputParser
        from langchain_core.prompts import PromptTemplate

        from app.ai.prompts import build_text_to_sql_prompt

        # A single LangChain Runnable chain regardless of provider — the
        # prompt template just passes through the already-built prompt string
        # (build_text_to_sql_prompt does the actual templating), then the
        # chosen LLM, then a plain string parser.
        chain = (
            PromptTemplate.from_template("{prompt}")
            | self.llm
            | StrOutputParser()
        )

        prompt = build_text_to_sql_prompt(question=question, tables_schema=tables_schema)
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
        sql = sql.strip()
        # A NO_ANSWER sentinel is returned verbatim (no semicolon coercion) so
        # the caller can detect it; see _parse_no_answer.
        if sql.upper().startswith("-- NO_ANSWER"):
            return sql
        # Ensure it ends with semicolon
        sql = sql.rstrip(";") + ";"
        return sql

    @staticmethod
    def _parse_no_answer(sql: str) -> str | None:
        """
        Detect the model's NO_ANSWER sentinel (`-- NO_ANSWER: <reason>`),
        returning the reason string, or None if the output is a real query.
        """
        stripped = sql.strip()
        if stripped.upper().startswith("-- NO_ANSWER"):
            reason = stripped.split(":", 1)[1].strip() if ":" in stripped else ""
            return reason or "The question cannot be answered from this dataset."
        return None

    # How many sample values to show the LLM per column. Sample values help the
    # model pick correct value literals (e.g. that status ∈ {'shipped','pending'})
    # without bloating the prompt.
    _PROMPT_SAMPLE_LIMIT = 3

    @classmethod
    def _format_schema(cls, columns_metadata: dict) -> str:
        lines = []
        for col, meta in columns_metadata.items():
            col_type = meta.get("type", "string").upper()
            nullable = "" if meta.get("nullable") else " NOT NULL"
            # Always show columns pre-quoted so the model mirrors this exact
            # form everywhere it references them (SELECT, WHERE, GROUP BY, ...) —
            # column names with spaces/special chars otherwise get inconsistently
            # quoted (e.g. quoted in GROUP BY but bare in SELECT, breaking the parser).
            samples = meta.get("sample_values") or []
            sample_str = ""
            if samples:
                shown = ", ".join(str(s) for s in samples[: cls._PROMPT_SAMPLE_LIMIT])
                sample_str = f"  -- e.g. {shown}"
            lines.append(f'  "{col}"  {col_type}{nullable}{sample_str}')
        return "\n".join(lines)

    @classmethod
    def _format_tables_schema(
        cls, tables: dict, relevant_columns: list[str] | None = None
    ) -> str:
        """
        Render all tables for the prompt as::

            -- Table: sales
              "region"  STRING NOT NULL  -- e.g. US, EU
              ...
            -- Table: customers
              ...

        `relevant_columns` (RAG) are table-qualified names (`"table.column"`).
        Filtering is coarsened to table granularity: a table with ANY retrieved
        column keeps ALL of its columns (so join keys are never filtered away);
        a table with none of its columns retrieved is dropped. When None (RAG
        unavailable / small schema), every column of every table is shown.
        """
        relevant = set(relevant_columns) if relevant_columns else None
        blocks = []
        for table_name, table_meta in tables.items():
            columns = table_meta.get("columns", {})
            # When RAG retrieved columns, keep a table only if at least one of
            # its qualified columns ("table.col") was retrieved; then keep ALL
            # its columns. Without retrieval, keep everything.
            if relevant is not None and not any(
                f"{table_name}.{col}" in relevant for col in columns
            ):
                continue
            blocks.append(f"-- Table: {table_name}\n{cls._format_schema(columns)}")
        # If per-table filtering removed everything (retrieval mismatch), fall
        # back to showing all tables rather than an empty schema.
        if not blocks:
            blocks = [
                f"-- Table: {name}\n{cls._format_schema(meta.get('columns', {}))}"
                for name, meta in tables.items()
            ]
        return "\n\n".join(blocks)

    _DATE_LIKE_KEYWORDS = ("date", "month", "year", "time", "week", "day", "quarter")

    @classmethod
    def _is_date_like(cls, col_name: str) -> bool:
        name = col_name.lower()
        return any(kw in name for kw in cls._DATE_LIKE_KEYWORDS)

    @classmethod
    def _suggest_visualization(cls, results: list[dict]) -> str:
        """
        Single source of truth for chart-type suggestion — this result is
        persisted on the Query row and the frontend renders it as-is rather
        than re-deriving its own guess.

        Cases handled, in order:
        1. No rows                                        -> table
        2. Exactly 1 dimension + 1 measure, dimension is
           date-like                                      -> line
        3. Exactly 1 dimension + 1 measure, few categories -> pie
        4. Exactly 1 dimension + 1 measure, many categories-> bar
        5. A date-like column + 2+ numeric measures        -> line
           (multi-series trend over time — NOT a scatter: the x-axis is a
           timeline, not a second independent numeric variable)
        6. No date-like column + 2+ numeric measures        -> scatter
           (true correlation between independent numeric variables)
        7. Fallback                                         -> bar
        """
        if not results:
            return "table"
        import pandas as pd
        df = pd.DataFrame(results)
        cols = list(df.columns)
        numeric_cols = [c for c in cols if pd.api.types.is_numeric_dtype(df[c])]
        non_numeric_cols = [c for c in cols if c not in numeric_cols]
        has_date_like = any(cls._is_date_like(c) for c in non_numeric_cols)

        if len(cols) == 2 and len(numeric_cols) == 1:
            if cls._is_date_like(cols[0]):
                return "line"
            if len(df) <= 8:
                return "pie"
            return "bar"

        if len(numeric_cols) >= 2:
            return "line" if has_date_like else "scatter"

        return "bar"
