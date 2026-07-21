"""
SQL executor using DuckDB — runs generated SQL directly against
CSV / Excel / JSON files without a separate database.

DuckDB is ideal here because:
- Zero-config, in-process OLAP engine
- Native CSV/Parquet/JSON reading
- Fast for analytical queries
- No data duplication needed
"""
from typing import Any

import duckdb
import structlog

from app.utils.file_parser import FileParser

logger = structlog.get_logger(__name__)

# Read-only operations allowed. Word-boundary matched (see _validate_sql_safety)
# so a legitimate column like "created_at" doesn't trip the "CREATE" rule.
_DANGEROUS_KEYWORDS = frozenset(
    ["DROP", "DELETE", "UPDATE", "INSERT", "CREATE", "ALTER", "TRUNCATE", "ATTACH"]
)

# DuckDB table/scalar functions that reach the filesystem or network. These are
# blocked at the engine level by enable_external_access=false (see execute()),
# but are also rejected here as an early, explicit first layer so a rejected
# query fails fast with a clear reason rather than a generic engine error.
_FILE_ACCESS_FUNCTIONS = frozenset(
    [
        "READ_CSV", "READ_CSV_AUTO", "READ_PARQUET", "READ_JSON",
        "READ_JSON_AUTO", "READ_NDJSON", "READ_TEXT", "READ_BLOB",
        "GLOB", "SNIFF_CSV", "COPY", "INSTALL", "LOAD",
    ]
)


class DatasetSQLExecutor:
    """Executes SQL against an uploaded dataset file via DuckDB."""

    def execute(self, sql: str, file_path: str, file_type: str) -> list[dict[str, Any]]:
        """
        Load the file into DuckDB as a virtual table and run the SQL.
        Returns results as a list of row dicts.
        """
        self._validate_sql_safety(sql)

        # Load file into a pandas DataFrame first (handles xlsx)
        parser = FileParser(db=None)
        df = parser.get_dataframe(file_path, file_type)

        # Run SQL via DuckDB (uses the df as a virtual table named 'data').
        #
        # Hardened config — defense in depth against LLM-generated SQL that
        # tries to reach outside the in-memory dataset. `enable_external_access`
        # off disables DuckDB's file/URL-reading table functions (read_csv,
        # read_parquet, read_json, httpfs, etc.), so even SQL like
        # `SELECT * FROM read_csv('/app/.env')` that slips past the keyword
        # denylist below is refused by the engine itself. `autoinstall/
        # autoload_known_extensions` off prevents pulling in extensions (e.g.
        # httpfs) that would re-open those capabilities. The registered
        # DataFrame is loaded in-process before this connection exists, so it
        # is unaffected by disabling external access.
        conn = duckdb.connect(
            database=":memory:",
            config={
                "enable_external_access": "false",
                "autoinstall_known_extensions": "false",
                "autoload_known_extensions": "false",
            },
        )
        try:
            conn.register("data", df)
            # Replace table name references — use 'data' as canonical table name
            normalized_sql = self._normalize_table_name(sql)
            result = conn.execute(normalized_sql).fetchdf()
            return result.to_dict(orient="records")
        except duckdb.Error as e:
            logger.error("SQL execution failed", sql=sql, error=str(e))
            raise ValueError(f"SQL execution error: {e}") from e
        finally:
            conn.close()

    @staticmethod
    def _validate_sql_safety(sql: str) -> None:
        import re

        # Tokenize into SQL identifiers/keywords so matching is word-boundary
        # aware — otherwise "created_at" trips CREATE and "updated" trips
        # UPDATE. Uppercased for case-insensitive comparison.
        tokens = {t.upper() for t in re.findall(r"[A-Za-z_][A-Za-z0-9_]*", sql)}

        blocked = tokens & (_DANGEROUS_KEYWORDS | _FILE_ACCESS_FUNCTIONS)
        if blocked:
            # Deterministic message regardless of set ordering.
            raise ValueError(f"Disallowed SQL operation: {sorted(blocked)[0]}")

        # Only a single statement is permitted — reject stacked queries even if
        # each keyword individually looked benign (the trailing ';' DuckDB adds
        # is fine; an interior ';' followed by more SQL is not).
        if ";" in sql.strip().rstrip(";"):
            raise ValueError("Multiple SQL statements are not allowed.")

    @staticmethod
    def _normalize_table_name(sql: str) -> str:
        """
        Replace any FROM <name> references with FROM data so DuckDB resolves
        the registered virtual table regardless of what the LLM named it.

        Handles three identifier forms:
        - Quoted (`Sales Data`, "Sales Data", [Sales Data]) — matched as a
          single unit so an embedded space doesn't leave the rest dangling.
        - Unquoted names with punctuation (e.g. a dataset named "traversal-test"
          → `FROM traversal-test`) — a bare \\w+ match would stop at the hyphen
          and rewrite to `FROM data-test`, which DuckDB then can't parse. The
          unquoted branch consumes everything up to the next SQL delimiter
          (whitespace, comma, semicolon, or parenthesis) so the whole table
          reference is replaced.
        """
        import re
        return re.sub(
            r'\bFROM\s+(?:`[^`]+`|"[^"]+"|\[[^\]]+\]|[^\s,;()]+)',
            "FROM data",
            sql,
            flags=re.IGNORECASE,
        )
