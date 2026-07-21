"""
Effective per-table schema for a dataset, with backward-compatible synthesis.

`Dataset.tables_metadata` is only populated for datasets parsed after the
multi-table feature landed. For older rows (and conceptually for every CSV/JSON
file) the dataset is a single table. This helper returns a uniform
``{table_name: {columns: {...}, ...}}`` view regardless, so callers never have
to special-case NULL `tables_metadata`.
"""
from typing import Any

from app.utils.identifiers import DEFAULT_TABLE_NAME


def effective_tables_metadata(
    tables_metadata: dict[str, Any] | None,
    columns_metadata: dict[str, Any] | None,
) -> dict[str, Any]:
    """
    Return the dataset's per-table metadata, synthesizing a single ``data``
    table from `columns_metadata` when `tables_metadata` is absent (pre-feature
    rows or single-table files).
    """
    if tables_metadata:
        return tables_metadata
    return {
        DEFAULT_TABLE_NAME: {
            "original_name": DEFAULT_TABLE_NAME,
            "columns": columns_metadata or {},
            "sheet_index": 0,
        }
    }
