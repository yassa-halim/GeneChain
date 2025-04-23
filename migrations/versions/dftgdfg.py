from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql
from database.connection import JSONField
import time

revision: str = 'dftgdfg'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.create_table(
        'gene_data',
        sa.Column('id', sa.String(length=255), nullable=False),
        sa.Column('gene_data', JSONField(), nullable=True),
        sa.Column('created_at', sa.BigInteger(), nullable=False, default=lambda: int(time.time() * 1000)),
        sa.Column('updated_at', sa.BigInteger(), nullable=False, default=lambda: int(time.time() * 1000), onupdate=lambda: int(time.time() * 1000)),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, default=False),
        sa.Column('owner_id', sa.String(length=255), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('id', name='uq_gene_data_id')
    )

    op.create_index(
        'ix_gene_data_created_at',
        'gene_data',
        ['created_at']
    )

    op.create_index(
        'ix_gene_data_updated_at',
        'gene_data',
        ['updated_at']
    )

    op.create_index(
        'ix_gene_data_is_deleted',
        'gene_data',
        ['is_deleted']
    )

    op.create_index(
        'ix_gene_data_owner_id',
        'gene_data',
        ['owner_id']
    )

def downgrade() -> None:
    op.drop_index('ix_gene_data_owner_id', table_name='gene_data')
    op.drop_index('ix_gene_data_is_deleted', table_name='gene_data')
    op.drop_index('ix_gene_data_updated_at', table_name='gene_data')
    op.drop_index('ix_gene_data_created_at', table_name='gene_data')
    op.drop_table('gene_data')
