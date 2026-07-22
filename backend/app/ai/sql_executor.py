"""
SQL executor using DuckDB — runs generated SQL directly against
CSV / Excel / JSON files without a separate database.

DuckDB is ideal here because:
- Zero-config, in-process OLAP engine
- Native CSV/Parquet/JSON reading
- Fast for analytical queries
- No data duplication needed
"""

import re
from typing import Any

import duckdb
import sqlglot
import structlog
from sqlglot import exp

from app.utils import FileParser

logger = structlog.get_logger(__name__)

# DuckDB table/scalar functions that reach the filesystem or network. Blocked
# at the engine level by enable_external_access=false (see execute()), and also
# rejected here as an early, explicit layer so a rejected query fails fast with
# a clear reason. Kept as belt-and-suspenders alongside the sqlglot AST checks.
_FILE_ACCESS_FUNCTIONS = frozenset(
    [
        "read_csv",
        "read_csv_auto",
        "read_parquet",
        "read_json",
        "read_json_auto",
        "read_ndjson",
        "read_text",
        "read_blob",
        "glob",
        "sniff_csv",
        "copy",
        "install",
        "load",
    ]
)


class DatasetSQLExecutor:
    """Executes SQL against an uploaded dataset's table(s) via DuckDB."""

    def execute(
        self,
        sql: str,
        file_path: str,
        file_type: str,
        known_tables: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Load every table in the file into DuckDB (each under its real sanitized
        name) and run the SQL. `known_tables` (when provided) is the set of
        table names the SQL is allowed to reference — the LLM was told exactly
        these names, so anything else is a hallucination or injection and is
        rejected before execution. Returns results as a list of row dicts.
        """
        # Read all tables first so validation can check against the real names.
        parser = FileParser()
        frames = parser.get_dataframes(file_path, file_type)
        allowed = set(known_tables) if known_tables else set(frames.keys())

        self._validate_sql(sql, allowed)

        # Hardened config — defense in depth. `enable_external_access=false`
        # disables DuckDB's file/URL-reading table functions (read_csv,
        # read_parquet, httpfs, …), so even SQL that slips past validation
        # can't read local files. `autoinstall/autoload_known_extensions=false`
        # prevents pulling in extensions that would re-open those capabilities.
        # The DataFrames are loaded in-process before this connection exists,
        # unaffected by disabling external access.
        conn = duckdb.connect(
            database=":memory:",
            config={
                "enable_external_access": "false",
                "autoinstall_known_extensions": "false",
                "autoload_known_extensions": "false",
            },
        )
        try:
            # Register every table under its real name so JOINs across sheets
            # work. No name rewriting — the LLM already knows these names.
            for name, df in frames.items():
                conn.register(name, df)
            result = conn.execute(sql).fetchdf()
            return result.to_dict(orient="records")
        except duckdb.Error as e:
            logger.error("SQL execution failed", sql=sql, error=str(e))
            raise ValueError(f"SQL execution error: {e}") from e
        finally:
            conn.close()

    @classmethod
    def _validate_sql(cls, sql: str, allowed_tables: set[str]) -> None:
        """
        Parser-based (sqlglot AST) validation — correctness over aggressiveness:
        1. Reject obvious file-access function names outright (fast pre-filter).
        2. Exactly one statement, and it is a SELECT (or a CTE wrapping one).
        3. Every referenced table is one of `allowed_tables`.
        Column-level validation is intentionally NOT done here: aliases,
        computed expressions, `*`, and CTE-derived columns make it prone to
        false positives, and the engine surfaces a clear error for a genuinely
        bad column anyway.
        """
        cls._reject_file_access_functions(sql)
        stmt = cls._parse_single_statement(sql)
        cls._require_select_only(stmt)
        cls._require_known_tables(stmt, allowed_tables)

    @staticmethod
    def _reject_file_access_functions(sql: str) -> None:
        """Defense in depth alongside the engine's enable_external_access=false —
        rejects obvious file/URL-reading function calls with an explicit reason."""
        lowered = sql.lower()
        for fn in _FILE_ACCESS_FUNCTIONS:
            if fn in lowered and re.search(rf"\b{re.escape(fn)}\s*\(", lowered):
                raise ValueError(f"Disallowed function: {fn}")

    @staticmethod
    def _parse_single_statement(sql: str) -> exp.Expression:
        try:
            statements = [s for s in sqlglot.parse(sql, read="duckdb") if s is not None]
        except Exception as e:
            raise ValueError(f"Could not parse SQL: {e}") from e
        if len(statements) != 1:
            raise ValueError("Exactly one SQL statement is allowed.")
        return statements[0]

    @staticmethod
    def _require_select_only(stmt: exp.Expression) -> None:
        """Allowlist by root node type — safer and less version-fragile than
        enumerating every forbidden DDL/DML class. A read-only query's root is a
        SELECT, a set operation (UNION/INTERSECT/EXCEPT), or a WITH/CTE wrapping
        one of those. Anything else (Insert/Update/Delete/Drop/Create/Alter*/
        TruncateTable/Pragma/Set/Command/…) is rejected."""
        allowed_roots = (exp.Select, exp.SetOperation, exp.Subquery)
        root = stmt.this if isinstance(stmt, exp.With) else stmt
        if not isinstance(root, allowed_roots):
            raise ValueError("Only read-only SELECT statements are allowed.")

    @staticmethod
    def _require_known_tables(stmt: exp.Expression, allowed_tables: set[str]) -> None:
        """Every referenced base table must be a known, registered table. CTE
        names defined in the same query are allowed (they're not base tables).
        As a bonus, this also catches file-reading table *functions* — they
        parse as anonymous functions, not as known Table nodes."""
        cte_names = {c.alias_or_name.lower() for c in stmt.find_all(exp.CTE)}
        for table in stmt.find_all(exp.Table):
            tname = (table.name or "").lower()
            if not tname or tname in cte_names:
                continue
            if tname not in allowed_tables:
                raise ValueError(
                    f"Unknown table '{table.name}'. Allowed tables: "
                    f"{', '.join(sorted(allowed_tables))}."
                )
