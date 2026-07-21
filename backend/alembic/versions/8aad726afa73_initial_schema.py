"""initial schema

Revision ID: 8aad726afa73
Revises: 
Create Date: 2026-07-18 13:20:24.815430

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import pgvector.sqlalchemy
from sqlalchemy.dialects import postgresql

revision: str = '8aad726afa73'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('documents',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('source', sa.String(length=50), nullable=False),
    sa.Column('ticker', sa.String(length=10), nullable=True),
    sa.Column('title', sa.String(length=500), nullable=True),
    sa.Column('chunk_count', sa.Integer(), nullable=False),
    sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('threads',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('title', sa.String(length=255), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('document_chunks',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('document_id', sa.UUID(), nullable=False),
    sa.Column('chunk_index', sa.Integer(), nullable=True),
    sa.Column('content', sa.Text(), nullable=True),
    sa.Column('section_title', sa.String(length=255), nullable=True),
    sa.Column('embedding', pgvector.sqlalchemy.Vector(768), nullable=True),
    sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(
        'ix_document_chunks_embedding_hnsw',
        'document_chunks',
        ['embedding'],
        postgresql_using='hnsw',
        postgresql_ops={'embedding': 'vector_cosine_ops'},
    )
    op.create_table('messages',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('thread_id', sa.UUID(), nullable=False),
    sa.Column('role', sa.String(length=20), nullable=False),
    sa.Column('content', sa.Text(), nullable=True),
    sa.Column('ui_blocks', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('tool_trace', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['thread_id'], ['threads.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.drop_table('playing_with_neon')


def downgrade() -> None:
    op.create_table('playing_with_neon',
    sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('name', sa.TEXT(), autoincrement=False, nullable=False),
    sa.Column('value', sa.REAL(), autoincrement=False, nullable=True),
    sa.PrimaryKeyConstraint('id', name=op.f('playing_with_neon_pkey'))
    )
    op.drop_table('messages')
    op.drop_index('ix_document_chunks_embedding_hnsw', table_name='document_chunks')
    op.drop_table('document_chunks')
    op.drop_table('threads')
    op.drop_table('documents')