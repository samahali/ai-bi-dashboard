"""
RAG (Retrieval-Augmented Generation) schema store, backed by ChromaDB.

Each dataset's columns are embedded as individual documents (table + name +
type + sample values) when the file finishes parsing. At query time, the
user's question is embedded and the most relevant columns (across ALL of the
dataset's tables) are retrieved and used to trim the schema injected into the
SQL-generation prompt — instead of always dumping every column of every table.

A dataset may contain multiple tables (Excel sheets). All of a dataset's
columns live in ONE collection, each document tagged with its table name, so a
single similarity query spans every table (needed to surface join keys and
answer cross-table questions). Retrieved columns are returned table-qualified
(`"table.column"`). Falls back to the full schema (behavior before this module
existed) if ChromaDB is unreachable — retrieval quality is never a hard
dependency for the core text-to-SQL feature.

Uses a lightweight deterministic hashing embedding (no ONNX/sentence-
transformers model download) — the column corpus is small, structured text
(names/types/sample values, not prose), where a hashing vectorizer is a
reasonable fit and keeps the app free of a ~80MB first-query model download.
"""
import chromadb
import contextlib
import hashlib
import math
import structlog
from app.config import settings
from chromadb import Documents, EmbeddingFunction, Embeddings
from collections import Counter
from typing import Any

logger = structlog.get_logger(__name__)

EMBEDDING_DIMENSIONS = 256

# Dynamic Top-K: retrieve a fraction of the total columns, bounded. Small
# schemas retrieve few (min); large schemas retrieve more (capped so the prompt
# stays bounded). See _dynamic_top_k.
TOP_K_RATIO = 0.5
TOP_K_MIN = 8
TOP_K_MAX = 30


def _dynamic_top_k(total_columns: int) -> int:
    """Columns to retrieve given the dataset's total column count, bounded to
    [TOP_K_MIN, TOP_K_MAX]."""
    scaled = math.ceil(total_columns * TOP_K_RATIO)
    return max(TOP_K_MIN, min(scaled, TOP_K_MAX))

# Module-level singleton ChromaDB client — mirrors the engine/AsyncSessionLocal
# pattern in db/session.py. Each of SchemaRAGStore's 3 call sites (agent.py,
# file_parser.py, dataset_service.py) constructs a fresh `SchemaRAGStore()`
# per call, but they all share this one HttpClient/connection instead of each
# opening its own, since chromadb.HttpClient is safe to share across callers
# within a process.
_client: chromadb.ClientAPI | None = None


def _get_shared_client() -> chromadb.ClientAPI:
    global _client
    if _client is None:
        _client = chromadb.HttpClient(
            host=settings.chromadb_host,
            port=settings.chromadb_port,
        )
    return _client


class HashingEmbeddingFunction(EmbeddingFunction):
    """
    Deterministic bag-of-tokens hashing embedding.

    Tokenizes on word boundaries, hashes each token into a fixed-size vector
    (the "hashing trick"), and L2-normalizes so cosine/L2 distance in
    ChromaDB behaves sensibly. No model weights, no network calls, fully
    reproducible across processes.
    """

    def __call__(self, input: Documents) -> Embeddings:
        return [self._embed_one(text) for text in input]

    @staticmethod
    def _embed_one(text: str) -> list[float]:
        tokens = HashingEmbeddingFunction._tokenize(text)
        vector = [0.0] * EMBEDDING_DIMENSIONS
        for token, count in Counter(tokens).items():
            idx = int(hashlib.md5(token.encode("utf-8")).hexdigest(), 16) % EMBEDDING_DIMENSIONS
            vector[idx] += count
        norm = math.sqrt(sum(v * v for v in vector)) or 1.0
        return [v / norm for v in vector]

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        import re
        # Split camelCase/snake_case/kebab-case column names into sub-words
        # so "customer_id" and "signup date" retrieve similarly to "customer id".
        text = re.sub(r"[_\-]", " ", text)
        text = re.sub(r"([a-z])([A-Z])", r"\1 \2", text)
        return re.findall(r"[a-zA-Z0-9]+", text.lower())


class SchemaRAGStore:
    """Embeds and retrieves dataset column context via ChromaDB."""

    def __init__(self) -> None:
        self._embedding_fn = HashingEmbeddingFunction()

    def _get_client(self) -> chromadb.ClientAPI:
        return _get_shared_client()

    @staticmethod
    def _collection_name(dataset_id: int) -> str:
        return f"dataset_{dataset_id}_schema"

    def index_dataset_schema(self, dataset_id: int, tables_metadata: dict[str, Any]) -> None:
        """
        Embed every column of every table in a dataset as a retrievable,
        table-tagged document. `tables_metadata` maps table_name → {columns:
        {col: {type, nullable, sample_values}}, ...}. Called after successful
        parsing. Best-effort: failures are logged, not raised — RAG context is
        an enhancement, not a requirement for text-to-SQL.
        """
        if not tables_metadata:
            return
        try:
            client = self._get_client()
            # Drop and recreate so re-parsing a dataset never leaves stale
            # documents behind (e.g. a renamed column or sheet).
            name = self._collection_name(dataset_id)
            with contextlib.suppress(Exception):
                client.delete_collection(name)
            collection = client.create_collection(name, embedding_function=self._embedding_fn)

            ids, documents, metadatas = [], [], []
            for table_name, table_meta in tables_metadata.items():
                for col, meta in (table_meta.get("columns") or {}).items():
                    col_type = meta.get("type", "string")
                    samples = meta.get("sample_values", [])
                    # Include the table name in the document so retrieval can
                    # match on table intent too, and qualify the id so columns
                    # of the same name in different sheets never collide.
                    doc = f"{table_name}.{col} ({col_type})"
                    if samples:
                        doc += f" — example values: {', '.join(str(s) for s in samples[:5])}"
                    ids.append(f"{table_name}.{col}")
                    documents.append(doc)
                    metadatas.append({
                        "table": table_name,
                        "column": col,
                        "type": col_type,
                        "nullable": bool(meta.get("nullable", False)),
                    })

            if ids:
                collection.add(ids=ids, documents=documents, metadatas=metadatas)
            logger.info(
                "Indexed dataset schema in ChromaDB",
                dataset_id=dataset_id, tables=len(tables_metadata), columns=len(ids),
            )
        except Exception as exc:
            logger.warning("Failed to index dataset schema in ChromaDB", dataset_id=dataset_id, error=str(exc))

    def retrieve_relevant_columns(self, dataset_id: int, question: str) -> list[str] | None:
        """
        Return the table-qualified column names (`"table.column"`) most relevant
        to `question`, or None if retrieval isn't available or the schema is
        small enough that retrieval wouldn't narrow anything down (caller then
        falls back to the full schema). Top-K scales with the dataset's total
        column count (see _dynamic_top_k).
        """
        try:
            client = self._get_client()
            collection = client.get_collection(
                self._collection_name(dataset_id), embedding_function=self._embedding_fn
            )
            total = collection.count()
            top_k = _dynamic_top_k(total)
            if total <= top_k:
                # Small schema — retrieval adds no value, use the full schema.
                return None
            result = collection.query(query_texts=[question], n_results=top_k)
            metadatas = result.get("metadatas") or [[]]
            # A collection indexed before table-tagging (older dataset) has no
            # "table" key; skip those entries — the caller falls back to full
            # schema if nothing qualified comes back.
            qualified = [
                f"{m['table']}.{m['column']}"
                for m in metadatas[0]
                if m.get("table") and m.get("column")
            ]
            if not qualified:
                return None
            logger.info(
                "RAG retrieved columns",
                dataset_id=dataset_id, total_columns=total, top_k=top_k, retrieved=len(qualified),
            )
            return qualified
        except Exception as exc:
            logger.warning("ChromaDB retrieval failed, falling back to full schema", dataset_id=dataset_id, error=str(exc))
            return None

    def delete_dataset_schema(self, dataset_id: int) -> None:
        """Clean up the collection when a dataset is deleted."""
        try:
            self._get_client().delete_collection(self._collection_name(dataset_id))
        except Exception as exc:
            logger.warning("Failed to delete ChromaDB collection", dataset_id=dataset_id, error=str(exc))
