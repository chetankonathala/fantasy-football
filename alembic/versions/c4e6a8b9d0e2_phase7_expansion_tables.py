"""phase7_expansion: nfl_draft_pick, team_depth_chart, schedule_strength, dynasty_projection, historical_rookie_comp

Revision ID: c4e6a8b9d0e2
Revises: b2d4e6f8a1c3
Create Date: 2026-04-30 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c4e6a8b9d0e2'
down_revision: Union[str, None] = 'b2d4e6f8a1c3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── nfl_draft_pick ────────────────────────────────────────────
    op.create_table(
        'nfl_draft_pick',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('draft_year', sa.Integer(), nullable=False),
        sa.Column('overall', sa.Integer(), nullable=False),
        sa.Column('round', sa.Integer(), nullable=False),
        sa.Column('pick_in_round', sa.Integer(), nullable=False),
        sa.Column('player_name', sa.String(length=100), nullable=False),
        sa.Column('position', sa.String(length=5), nullable=True),
        sa.Column('college', sa.String(length=100), nullable=True),
        sa.Column('college_full', sa.String(length=150), nullable=True),
        sa.Column('nfl_team', sa.String(length=5), nullable=True),
        sa.Column('nfl_team_id', sa.String(length=10), nullable=True),
        sa.Column('nfl_team_name', sa.String(length=100), nullable=True),
        sa.Column('nfl_team_logo', sa.String(length=300), nullable=True),
        sa.Column('espn_athlete_id', sa.String(length=20), nullable=True),
        sa.Column('traded', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('trade_note', sa.String(length=300), nullable=True),
        sa.Column('headshot_url', sa.String(length=300), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('draft_year', 'overall', name='uq_nfl_draft_year_overall'),
    )
    with op.batch_alter_table('nfl_draft_pick') as batch_op:
        batch_op.create_index('ix_nfl_draft_pick_draft_year', ['draft_year'])

    # ── team_depth_chart ──────────────────────────────────────────
    op.create_table(
        'team_depth_chart',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('team', sa.String(length=5), nullable=False),
        sa.Column('position', sa.String(length=5), nullable=False),
        sa.Column('depth_order', sa.Integer(), nullable=False),
        sa.Column('player_name', sa.String(length=100), nullable=False),
        sa.Column('sleeper_id', sa.String(length=20), nullable=True),
        sa.Column('age', sa.Float(), nullable=True),
        sa.Column('dynasty_value', sa.Integer(), nullable=True),
        sa.Column('dynasty_position_rank', sa.Integer(), nullable=True),
        sa.Column('is_rookie', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('season', sa.Integer(), nullable=False, server_default=sa.text('2026')),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('season', 'team', 'position', 'depth_order', name='uq_depth_team_pos_order'),
    )
    with op.batch_alter_table('team_depth_chart') as batch_op:
        batch_op.create_index('ix_team_depth_chart_team', ['team'])

    # ── schedule_strength ─────────────────────────────────────────
    op.create_table(
        'schedule_strength',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('season', sa.Integer(), nullable=False),
        sa.Column('team', sa.String(length=5), nullable=False),
        sa.Column('position', sa.String(length=5), nullable=False),
        sa.Column('sos_score', sa.Float(), nullable=False),
        sa.Column('sos_rank', sa.Integer(), nullable=True),
        sa.Column('avg_opp_dvp_rank', sa.Float(), nullable=True),
        sa.Column('games_played', sa.Integer(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('season', 'team', 'position', name='uq_sos_season_team_pos'),
    )
    with op.batch_alter_table('schedule_strength') as batch_op:
        batch_op.create_index('ix_schedule_strength_team', ['team'])

    # ── dynasty_projection ────────────────────────────────────────
    op.create_table(
        'dynasty_projection',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('player_name', sa.String(length=100), nullable=False),
        sa.Column('sleeper_id', sa.String(length=20), nullable=True),
        sa.Column('position', sa.String(length=5), nullable=True),
        sa.Column('base_year', sa.Integer(), nullable=False),
        sa.Column('projection_year', sa.Integer(), nullable=False),
        sa.Column('projected_value', sa.Integer(), nullable=False),
        sa.Column('projected_age', sa.Float(), nullable=True),
        sa.Column('decay_factor', sa.Float(), nullable=True),
        sa.Column('role_label', sa.String(length=30), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('player_name', 'base_year', 'projection_year', name='uq_proj_player_year'),
    )
    with op.batch_alter_table('dynasty_projection') as batch_op:
        batch_op.create_index('ix_dynasty_projection_player_name', ['player_name'])
        batch_op.create_index('ix_dynasty_projection_sleeper_id', ['sleeper_id'])

    # ── historical_rookie_comp ────────────────────────────────────
    op.create_table(
        'historical_rookie_comp',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('player_name', sa.String(length=100), nullable=False),
        sa.Column('season', sa.Integer(), nullable=False),
        sa.Column('position', sa.String(length=5), nullable=False),
        sa.Column('nfl_round', sa.Integer(), nullable=True),
        sa.Column('nfl_pick', sa.Integer(), nullable=True),
        sa.Column('college', sa.String(length=100), nullable=True),
        sa.Column('nfl_team', sa.String(length=5), nullable=True),
        sa.Column('age_at_draft', sa.Float(), nullable=True),
        sa.Column('year1_ppr_points', sa.Float(), nullable=True),
        sa.Column('year1_games', sa.Integer(), nullable=True),
        sa.Column('year1_starts', sa.Integer(), nullable=True),
        sa.Column('year1_target_share', sa.Float(), nullable=True),
        sa.Column('year1_carry_share', sa.Float(), nullable=True),
        sa.Column('hit_label', sa.String(length=20), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('player_name', 'season', name='uq_hist_rookie_player_season'),
    )


def downgrade() -> None:
    op.drop_table('historical_rookie_comp')
    op.drop_table('dynasty_projection')
    op.drop_table('schedule_strength')
    op.drop_table('team_depth_chart')
    op.drop_table('nfl_draft_pick')
