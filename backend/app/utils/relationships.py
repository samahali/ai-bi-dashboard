"""
Heuristic detection of LIKELY join relationships between a dataset's tables.

Deliberately conservative and name-based only (no value inspection): if the
same column name — after normalizing away casing/separator differences —
appears in two different tables and looks like an identifier, it's reported as
a *likely* relationship with a confidence score. Never guaranteed. The caller
(the SQL-generation prompt) is responsible for framing these as hints the LLM
may use, not facts, and for explicitly forbidding invented joins when none are
found.
"""

import re
from itertools import combinations
from typing import Any

# A column name "looks like" an identifier if it contains "id" as a distinct
# word/segment (e.g. customer_id, CustomerID, id) — used only to raise/lower
# confidence, never to gate detection outright (a shared exact name is still
# reported even if it doesn't look id-like, just at lower confidence).
_ID_LIKE = re.compile(r"(^|_)id($|_)|id$", re.IGNORECASE)


def normalize_column_name(name: str) -> str:
    """
    Canonicalize a column name for cross-table comparison so that
    `customer_id`, `customerId`, `CustomerID`, `Customer Id`, and
    `customer-id` are all treated as the same underlying name: split
    camelCase, lowercase, strip separators.
    """
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", name)  # camelCase -> camel_Case
    s = re.sub(r"[\s\-]+", "_", s)  # spaces/hyphens -> _
    s = re.sub(r"_+", "_", s).strip("_")
    return s.lower()


def _looks_id_like(original_name: str) -> bool:
    return bool(_ID_LIKE.search(original_name))


def detect_relationships(tables_metadata: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Given the dataset's `tables_metadata` ({table: {columns: {...}}}), return a
    list of likely relationships:
    ``[{from_table, to_table, column, normalized, confidence}]``.

    A candidate relationship exists whenever two different tables each have a
    column whose *normalized* name matches. Confidence:
    - 0.9 — the original column names are identical (not just normalized).
    - 0.7 — only the normalized forms match (casing/separator differs).
    Both cases get a +0.05 nudge (capped at 0.95) when the name looks id-like,
    since that's the strongest signal of an actual foreign-key relationship
    rather than a coincidentally-shared descriptive column (e.g. "region").
    Only id-like names are reported at all — a shared non-id name (e.g. both
    tables have a "region" column) is common and not a join key, so reporting
    it would push the LLM toward spurious joins.
    """
    table_names = list(tables_metadata.keys())
    if len(table_names) < 2:
        return []

    # table -> {normalized_name: original_name} (first occurrence wins)
    by_table: dict[str, dict[str, str]] = {}
    for table in table_names:
        columns = (tables_metadata[table].get("columns") or {}).keys()
        normalized: dict[str, str] = {}
        for col in columns:
            if not _looks_id_like(col):
                continue
            norm = normalize_column_name(col)
            normalized.setdefault(norm, col)
        by_table[table] = normalized

    relationships: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for table_a, table_b in combinations(table_names, 2):
        cols_a, cols_b = by_table[table_a], by_table[table_b]
        for norm, original_a in cols_a.items():
            if norm not in cols_b:
                continue
            original_b = cols_b[norm]
            key = (table_a, table_b, norm)
            if key in seen:
                continue
            seen.add(key)

            confidence = 0.9 if original_a == original_b else 0.7
            confidence = min(confidence + 0.05, 0.95)  # already id-like by construction

            relationships.append(
                {
                    "from_table": table_a,
                    "to_table": table_b,
                    "column": original_a,
                    "to_column": original_b,
                    "normalized": norm,
                    "confidence": round(confidence, 2),
                }
            )

    # Highest-confidence first, for prompt rendering priority.
    relationships.sort(key=lambda r: r["confidence"], reverse=True)
    return relationships
