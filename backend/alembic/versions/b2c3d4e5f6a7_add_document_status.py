"""add document status column

Revision ID: b2c3d4e5f6a7
Revises: 8aad726afa73
Create Date: 2026-07-22 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, Sequence[str], None] = '8aad726afa73'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add status column with server_default so existing rows get a value.
    # Existing rows are assumed to be fully ingested ('ready').
    # New rows created by the ORM will use the Python default ('processing').
    op.add_column('documents', sa.Column(
        'status', sa.String(length=20),
        server_default='ready',
        nullable=False,
    ))


def downgrade() -> None:
    op.drop_column('documents', 'status')
