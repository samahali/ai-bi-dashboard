"""
SQL-identifier sanitization for table names.

Excel sheet names allow spaces, punctuation, leading digits, and mixed case;
DuckDB table identifiers need to be safe, unquoted, lowercase snake_case. The
sanitized name is the single canonical identifier that MUST agree across three
places: the `tables_metadata` keys, the DuckDB `conn.register(name, df)` call,
and the schema block shown to the LLM in the prompt. Keeping this in one helper
guarantees they never drift apart.
"""

import re

# CSV/JSON files are conceptually a single table; this stable name preserves the
# pre-multi-table behavior (the executor used to register the frame as "data").
DEFAULT_TABLE_NAME = "data"


def sanitize_table_name(raw: str) -> str:
    """
    Turn an arbitrary sheet/table name into a safe lowercase snake_case SQL
    identifier: lowercase, non-[a-z0-9_] → '_', collapse repeats, strip edge
    underscores, prefix 't_' if it starts with a digit or is empty.

    Collision de-duplication across a set of names is handled separately by
    `sanitize_table_names` (a single name can't know about its siblings).
    """
    name = raw.strip().lower()
    name = re.sub(r"[^a-z0-9_]+", "_", name)
    name = re.sub(r"_+", "_", name).strip("_")
    if not name or name[0].isdigit():
        name = f"t_{name}" if name else "table"
    return name


def sanitize_table_names(raw_names: list[str]) -> dict[str, str]:
    """
    Sanitize a list of raw sheet names into unique canonical identifiers,
    preserving order. Returns {raw_name: sanitized_name}. Collisions (two
    sheets that sanitize to the same identifier, e.g. "Sales!" and "Sales?")
    get a numeric suffix (_2, _3, …) so every DuckDB table name stays unique.
    """
    seen: dict[str, int] = {}
    mapping: dict[str, str] = {}
    for raw in raw_names:
        base = sanitize_table_name(raw)
        if base in seen:
            seen[base] += 1
            mapping[raw] = f"{base}_{seen[base]}"
        else:
            seen[base] = 1
            mapping[raw] = base
    return mapping
