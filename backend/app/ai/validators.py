"""
Prompt injection validator.
Prevents users from hijacking the LLM via crafted questions.
"""

import re
from typing import Tuple

# Patterns that indicate prompt injection or SQL injection attempts.
#
# This is a best-effort FIRST layer only — a static blocklist is inherently
# bypassable by paraphrase/translation/encoding. The real guarantees live
# downstream: the SQL-generation prompt delimits and neutralizes the question
# (see build_text_to_sql_prompt), and the DuckDB executor runs with external
# file/URL access disabled plus a keyword/function denylist (see
# sql_executor.py). This layer just rejects the obvious attempts early.
_INJECTION_PATTERNS: list[str] = [
    r"ignore\s+(the\s+)?(previous|above|all|prior|preceding)",
    r"disregard\s+(all|the|previous|prior|everything)",
    r"new\s+instructions?",
    r"system\s+(message|prompt)",
    r"you\s+are\s+(now|a|an)",
    r"act\s+as",
    r"pretend\s+(you|to)",
    r"jailbreak",
    r"forget\s+(everything|all|previous|prior)",
    r"reveal\s+(the\s+)?(prompt|instructions?|system)",
    r"repeat\s+(the\s+)?(prompt|instructions?|everything\s+above)",
    r"\b(read_csv|read_parquet|read_json|read_text|read_blob)\b",  # file-access funcs
    r"\b(INSERT\s+INTO|DELETE\s+FROM|DROP\s+TABLE|ALTER\s+TABLE|TRUNCATE\s+TABLE)\b",
    r"\bUPDATE\b\s+\w+\s+\bSET\b",  # UPDATE ... SET (word-bounded; won't hit "updated")
    r"--\s*$",  # SQL comment injection
    r";\s*\b(DROP|DELETE|UPDATE|INSERT)\b",
    r"<<<|>>>",  # attempt to spoof the prompt's question delimiters
]

_COMPILED = [re.compile(p, re.IGNORECASE) for p in _INJECTION_PATTERNS]

MAX_QUESTION_LENGTH = 2000


class PromptInjectionValidator:
    @staticmethod
    def validate(question: str) -> Tuple[bool, str]:
        """
        Returns (is_valid, rejection_reason).
        """
        if not question or not question.strip():
            return False, "Question cannot be empty."

        if len(question) > MAX_QUESTION_LENGTH:
            return False, f"Question too long (max {MAX_QUESTION_LENGTH} chars)."

        for pattern in _COMPILED:
            if pattern.search(question):
                return False, "Question contains disallowed content."

        # Reject excessive special characters (likely injection attempt)
        special_ratio = sum(
            1 for c in question if not c.isalnum() and c not in " ?.,'-"
        ) / len(question)
        if special_ratio > 0.4:
            return False, "Too many special characters in question."

        return True, "OK"
