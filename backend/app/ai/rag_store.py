"""
RAG (Retrieval-Augmented Generation) schema store, backed by ChromaDB.

Each dataset's columns are embedded as individual documents (name + type +
sample values) when the file finishes parsing. At query time, the user's
question is embedded and the top-K most relevant columns are retrieved and
injected into the SQL-generation prompt — instead of always dumping the
dataset's full column list.

This scales the same way regardless of column count: a 200-column dataset
sends the LLM only the ~15 columns actually relevant to the question, not
the whole schema. Falls back to the full schema (behavior before this
module existed) if ChromaDB is unreachable, since retrieval quality should
never be a hard dependency for the core text-to-SQL feature.

Uses a lightweight deterministic hashing embedding (no ONNX/sentence-
transformers model download) — the column corpus is small, structured text
(names/types/sample values, not prose), where a hashing vectorizer is a
reasonable fit and keeps the app free of a ~80MB first-query model
download and any dependency on external model registries.
"""
import hashlib
import math
from collections import Counter
from typing import Any

import chromadb
import structlog
from chromadb import Documents, EmbeddingFunction, Embeddings

from app.config import settings

logger = structlog.get_logger(__name__)

EMBEDDING_DIMENSIONS = 256
TOP_K_COLUMNS = 15


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
        self._client: chromadb.ClientAPI | None = None
        self._embedding_fn = HashingEmbeddingFunction()

    def _get_client(self) -> chromadb.ClientAPI:
        if self._client is None:
            self._client = chromadb.HttpClient(
                host=settings.chromadb_host,
                port=settings.chromadb_port,
            )
        return self._client

    @staticmethod
    def _collection_name(dataset_id: int) -> str:
        return f"dataset_{dataset_id}_schema"

    def index_dataset_schema(self, dataset_id: int, columns_metadata: dict[str, Any]) -> None:
        """
        Embed each column of a dataset as a retrievable document.
        Called after successful upload parsing. Best-effort: failures are
        logged, not raised — RAG context is an enhancement, not a
        requirement for text-to-SQL to function.
        """
        if not columns_metadata:
            return
        try:
            client = self._get_client()
            # Drop and recreate so re-parsing a dataset never leaves stale
            # column documents behind (e.g. a column that got renamed/removed).
            name = self._collection_name(dataset_id)
            try:
                client.delete_collection(name)
            except Exception:
                pass
            collection = client.create_collection(name, embedding_function=self._embedding_fn)

            ids, documents, metadatas = [], [], []
            for col, meta in columns_metadata.items():
                col_type = meta.get("type", "string")
                samples = meta.get("sample_values", [])
                doc = f"{col} ({col_type})"
                if samples:
                    doc += f" — example values: {', '.join(str(s) for s in samples[:5])}"
                ids.append(col)
                documents.append(doc)
                metadatas.append({
                    "column": col,
                    "type": col_type,
                    "nullable": bool(meta.get("nullable", False)),
                })

            collection.add(ids=ids, documents=documents, metadatas=metadatas)
            logger.info("Indexed dataset schema in ChromaDB", dataset_id=dataset_id, columns=len(ids))
        except Exception as exc:
            logger.warning("Failed to index dataset schema in ChromaDB", dataset_id=dataset_id, error=str(exc))

    def retrieve_relevant_columns(
        self, dataset_id: int, question: str, top_k: int = TOP_K_COLUMNS
    ) -> list[str] | None:
        """
        Return the column names most relevant to `question`, or None if
        retrieval isn't available (falls back to full schema upstream).
        """
        try:
            client = self._get_client()
            collection = client.get_collection(
                self._collection_name(dataset_id), embedding_function=self._embedding_fn
            )
            if collection.count() <= top_k:
                # Small schema — retrieval adds no value, return everything.
                return None
            result = collection.query(query_texts=[question], n_results=top_k)
            metadatas = result.get("metadatas") or [[]]
            return [m["column"] for m in metadatas[0]]
        except Exception as exc:
            logger.warning("ChromaDB retrieval failed, falling back to full schema", dataset_id=dataset_id, error=str(exc))
            return None

    def delete_dataset_schema(self, dataset_id: int) -> None:
        """Clean up the collection when a dataset is deleted."""
        try:
            self._get_client().delete_collection(self._collection_name(dataset_id))
        except Exception as exc:
            logger.warning("Failed to delete ChromaDB collection", dataset_id=dataset_id, error=str(exc))
