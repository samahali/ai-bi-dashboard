"""multi-table metadata

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-21

Adds nullable JSON columns to `datasets` for multi-table (Excel multi-sheet)
support:
- `tables_metadata`: per-table schema keyed by sanitized table name.
- `table_relationships`: heuristically-detected likely join relationships.

No data backfill: existing rows keep `tables_metadata = NULL` and are treated
as a single table synthesized lazily from `columns_metadata` + `file_type`, so
pre-existing datasets continue to work unchanged.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("datasets", sa.Column("tables_metadata", sa.JSON(), nullable=True))
    op.add_column(
        "datasets", sa.Column("table_relationships", sa.JSON(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("datasets", "table_relationships")
    op.drop_column("datasets", "tables_metadata")
