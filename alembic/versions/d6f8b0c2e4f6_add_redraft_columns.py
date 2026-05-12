"""add redraft columns to dynasty_value

Revision ID: d6f8b0c2e4f6
Revises: c4e6a8b9d0e2
Create Date: 2026-04-30 13:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd6f8b0c2e4f6'
down_revision: Union[str, None] = 'c4e6a8b9d0e2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('dynasty_value') as batch_op:
        batch_op.add_column(sa.Column('redraft_value', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('redraft_overall_rank', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('redraft_position_rank', sa.Integer(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('dynasty_value') as batch_op:
        batch_op.drop_column('redraft_position_rank')
        batch_op.drop_column('redraft_overall_rank')
        batch_op.drop_column('redraft_value')
