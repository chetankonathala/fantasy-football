"""add_rookie_pick_and_offseason_move

Revision ID: b2d4e6f8a1c3
Revises: a3f8c2e1d9b4
Create Date: 2026-04-29 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b2d4e6f8a1c3'
down_revision: Union[str, None] = 'a3f8c2e1d9b4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'rookie_pick',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('sleeper_id', sa.String(length=20), nullable=True),
        sa.Column('player_name', sa.String(length=100), nullable=False),
        sa.Column('position', sa.String(length=5), nullable=True),
        sa.Column('team', sa.String(length=5), nullable=True),
        sa.Column('college', sa.String(length=100), nullable=True),
        sa.Column('nfl_round', sa.Integer(), nullable=True),
        sa.Column('nfl_pick', sa.Integer(), nullable=True),
        sa.Column('age', sa.Float(), nullable=True),
        sa.Column('dynasty_value', sa.Integer(), nullable=True),
        sa.Column('dynasty_overall_rank', sa.Integer(), nullable=True),
        sa.Column('dynasty_position_rank', sa.Integer(), nullable=True),
        sa.Column('opportunity_grade', sa.String(length=2), nullable=True),
        sa.Column('opportunity_note', sa.String(length=200), nullable=True),
        sa.Column('year1_projection', sa.Float(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('player_name'),
    )
    with op.batch_alter_table('rookie_pick') as batch_op:
        batch_op.create_index('ix_rookie_pick_sleeper_id', ['sleeper_id'])

    op.create_table(
        'offseason_move',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('sleeper_id', sa.String(length=20), nullable=True),
        sa.Column('player_name', sa.String(length=100), nullable=False),
        sa.Column('position', sa.String(length=5), nullable=True),
        sa.Column('from_team', sa.String(length=5), nullable=True),
        sa.Column('to_team', sa.String(length=5), nullable=True),
        sa.Column('move_type', sa.String(length=20), nullable=False),
        sa.Column('fantasy_impact', sa.String(length=10), nullable=True),
        sa.Column('impact_direction', sa.String(length=10), nullable=True),
        sa.Column('impact_note', sa.String(length=300), nullable=True),
        sa.Column('dynasty_value', sa.Integer(), nullable=True),
        sa.Column('move_season', sa.Integer(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('sleeper_id', 'move_season', 'move_type', name='uq_offseason_move'),
    )
    with op.batch_alter_table('offseason_move') as batch_op:
        batch_op.create_index('ix_offseason_move_sleeper_id', ['sleeper_id'])


def downgrade() -> None:
    op.drop_table('offseason_move')
    op.drop_table('rookie_pick')
