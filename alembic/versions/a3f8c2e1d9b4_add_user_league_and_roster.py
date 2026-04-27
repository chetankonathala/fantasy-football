"""add_user_league_and_roster

Revision ID: a3f8c2e1d9b4
Revises: 5e62b2f30854
Create Date: 2026-04-27 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a3f8c2e1d9b4'
down_revision: Union[str, None] = '5e62b2f30854'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'user_league',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.String(length=100), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('scoring_format', sa.String(length=10), nullable=False),
        sa.Column('num_teams', sa.Integer(), nullable=False),
        sa.Column('draft_session_id', sa.String(length=36), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['draft_session_id'], ['draft_session.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_user_league_user_id', 'user_league', ['user_id'])

    op.create_table(
        'user_roster_player',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('league_id', sa.Integer(), nullable=False),
        sa.Column('player_id', sa.Integer(), nullable=False),
        sa.Column('position_slot', sa.String(length=10), nullable=False),
        sa.Column('added_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['league_id'], ['user_league.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['player_id'], ['player.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('league_id', 'player_id', name='uq_roster_league_player'),
    )


def downgrade() -> None:
    op.drop_table('user_roster_player')
    op.drop_index('ix_user_league_user_id', table_name='user_league')
    op.drop_table('user_league')
