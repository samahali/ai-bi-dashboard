"""
File parser utility — reads CSV / Excel / JSON files into pandas DataFrames,
infers column metadata, and updates the Dataset record.

A CSV or JSON file is a single table. An Excel workbook may contain multiple
sheets, each of which becomes its own table. To keep one code path for all
file types, every reader returns an ordered ``{table_name: DataFrame}`` mapping
(CSV/JSON yield exactly one entry named ``data``; Excel yields one entry per
sheet, keyed by the sanitized sheet name).
"""
from typing import Any

import pandas as pd
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Dataset, Insight
from app.db.session import AsyncSessionLocal
from app.utils.identifiers import DEFAULT_TABLE_NAME, sanitize_table_names
from app.utils.insight_generator import InsightGenerator
from app.utils.relationships import detect_relationships

logger = structlog.get_logger(__name__)

# Max rows to store in columns_metadata as sample values
SAMPLE_SIZE = 5


class FileParser:
    def __init__(self, db: AsyncSession | None = None) -> None:
        # `db` is only used by get_dataframe() (called within an existing request session).
        # parse_and_index() always opens its own session since it runs as a detached
        # background task outside the request's session lifecycle.
        self.db = db

    async def parse_and_index(self, dataset_id: int, file_path: str, file_type: str) -> None:
        """
        Parse the file, infer column metadata, and update the Dataset status.
        Called as a background task after upload — opens its own DB session
        since the request session that spawned it may already be closed.
        """
        async with AsyncSessionLocal() as db:
            try:
                # Read every table once; build metadata from the same frames
                # (no second read of the file).
                named = self._read_named_frames(file_path, file_type)
                tables_metadata = self._build_tables_metadata(named)

                # The primary (first) table stays in columns_metadata / row_count /
                # column_count so existing single-table consumers (frontend,
                # preview, pre-multi-table code paths) keep working unchanged.
                primary_name = next(iter(named))
                primary_df = named[primary_name][1]

                result = await db.execute(select(Dataset).where(Dataset.id == dataset_id))
                dataset = result.scalar_one_or_none()
                if not dataset:
                    logger.warning("Dataset not found during parsing", dataset_id=dataset_id)
                    return

                dataset.row_count = len(primary_df)
                dataset.column_count = len(primary_df.columns)
                dataset.columns_metadata = tables_metadata[primary_name]["columns"]
                dataset.tables_metadata = tables_metadata
                dataset.table_relationships = detect_relationships(tables_metadata)
                dataset.status = "ready"

                await db.commit()
                logger.info(
                    "Dataset parsed successfully",
                    dataset_id=dataset_id,
                    tables=len(named),
                    rows=len(primary_df),
                    relationships=len(dataset.table_relationships),
                )

                # Insights per table: {name: (original_name, df)} -> generate
                # independently per sheet, tagged with its table name.
                dataframes_by_table = {name: df for name, (_orig, df) in named.items()}
                await self._generate_insights(db, dataset_id, dataset.user_id, dataframes_by_table)

                from app.ai.rag_store import SchemaRAGStore
                SchemaRAGStore().index_dataset_schema(dataset_id, tables_metadata)

            except Exception as exc:
                logger.error("Failed to parse dataset", dataset_id=dataset_id, error=str(exc))
                await db.rollback()
                result = await db.execute(select(Dataset).where(Dataset.id == dataset_id))
                dataset = result.scalar_one_or_none()
                if dataset:
                    dataset.status = "error"
                    dataset.error_message = str(exc)
                    await db.commit()

    async def _generate_insights(
        self, db: AsyncSession, dataset_id: int, user_id: int, dataframes_by_table: dict[str, pd.DataFrame]
    ) -> None:
        """
        Run statistical insight detection independently per table and persist
        results, each tagged with the table it came from (via insight_metadata
        — no schema change needed). CSV/JSON have exactly one table, so this
        is identical to the pre-multi-table behavior for them.

        Failures here are logged but never fail the dataset itself — insights
        are a bonus on top of a successfully-parsed dataset, not a requirement.
        A failure on one table's insights doesn't stop the others.
        """
        total = 0
        for table_name, df in dataframes_by_table.items():
            try:
                insight_dicts = InsightGenerator().generate(df)
                for data in insight_dicts:
                    metadata = dict(data.get("insight_metadata") or {})
                    metadata["table"] = table_name
                    data = {**data, "insight_metadata": metadata}
                    db.add(Insight(dataset_id=dataset_id, user_id=user_id, **data))
                if insight_dicts:
                    await db.commit()
                    total += len(insight_dicts)
            except Exception as exc:
                logger.error(
                    "Failed to generate insights for table",
                    dataset_id=dataset_id, table=table_name, error=str(exc),
                )
                await db.rollback()
        if total:
            logger.info("Insights generated", dataset_id=dataset_id, count=total)

    def _read_file(self, file_path: str, file_type: str) -> pd.DataFrame:
        """Read the primary (single, or first-sheet) table as one DataFrame.

        Kept for the preview path and any single-table consumer. Multi-table
        code paths use `get_dataframes` / `_read_named_frames` instead.
        """
        if file_type == "csv":
            return pd.read_csv(file_path, low_memory=False)
        elif file_type == "excel":
            return pd.read_excel(file_path, engine="openpyxl")
        elif file_type == "json":
            return pd.read_json(file_path)
        raise ValueError(f"Unsupported file type: {file_type}")

    def get_dataframes(self, file_path: str, file_type: str) -> dict[str, pd.DataFrame]:
        """
        Public: read every table into an ordered ``{table_name: DataFrame}``
        mapping keyed by sanitized SQL-safe table name. Used by the SQL
        executor to register all tables in DuckDB. CSV/JSON → single entry
        ``data``; Excel → one entry per sheet.
        """
        return {name: df for name, (_orig, df) in self._read_named_frames(file_path, file_type).items()}

    def _read_named_frames(
        self, file_path: str, file_type: str
    ) -> dict[str, tuple[str, pd.DataFrame]]:
        """
        Read all tables, each value ``(original_name, DataFrame)`` so the
        original (pre-sanitization) sheet name is retained for display. Keyed
        by sanitized table name; insertion order = sheet order.
        """
        if file_type == "csv":
            return {DEFAULT_TABLE_NAME: (DEFAULT_TABLE_NAME, pd.read_csv(file_path, low_memory=False))}
        if file_type == "json":
            return {DEFAULT_TABLE_NAME: (DEFAULT_TABLE_NAME, pd.read_json(file_path))}
        if file_type == "excel":
            # sheet_name=None → ordered dict {original_sheet_name: DataFrame}.
            sheets: dict[str, pd.DataFrame] = pd.read_excel(
                file_path, engine="openpyxl", sheet_name=None
            )
            if not sheets:
                raise ValueError("Excel workbook contains no sheets.")
            name_map = sanitize_table_names(list(sheets.keys()))
            return {name_map[orig]: (orig, df) for orig, df in sheets.items()}
        raise ValueError(f"Unsupported file type: {file_type}")

    def _build_tables_metadata(
        self, named: dict[str, tuple[str, pd.DataFrame]]
    ) -> dict[str, Any]:
        """
        Build the per-table metadata blob stored on `Dataset.tables_metadata`
        from already-read frames (no file I/O here):
        ``{table_name: {original_name, row_count, column_count, columns, sheet_index}}``.
        `columns` reuses the exact shape produced by `_infer_metadata`, so the
        primary table's `columns` is drop-in compatible with `columns_metadata`.
        """
        tables: dict[str, Any] = {}
        for index, (name, (original_name, df)) in enumerate(named.items()):
            tables[name] = {
                "original_name": original_name,
                "row_count": len(df),
                "column_count": len(df.columns),
                "sheet_index": index,
                "columns": self._infer_metadata(df),
            }
        return tables

    def _infer_metadata(self, df: pd.DataFrame) -> dict[str, Any]:
        metadata: dict[str, Any] = {}
        for col in df.columns:
            series = df[col]
            dtype = series.dtype
            col_type = self._pandas_type_to_str(dtype)
            samples = [
                v for v in series.dropna().head(SAMPLE_SIZE).tolist()
                if v is not None
            ]
            metadata[str(col)] = {
                "type": col_type,
                "nullable": bool(series.isna().any()),
                "sample_values": samples,
            }
        return metadata

    @staticmethod
    def _pandas_type_to_str(dtype) -> str:
        if pd.api.types.is_integer_dtype(dtype):
            return "integer"
        if pd.api.types.is_float_dtype(dtype):
            return "float"
        if pd.api.types.is_bool_dtype(dtype):
            return "boolean"
        if pd.api.types.is_datetime64_any_dtype(dtype):
            return "datetime"
        return "string"

    def get_dataframe(self, file_path: str, file_type: str) -> pd.DataFrame:
        """Public method for services that need to work with the raw DataFrame."""
        return self._read_file(file_path, file_type)
