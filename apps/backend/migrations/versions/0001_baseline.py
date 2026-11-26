"""baseline

Revision ID: 0001_baseline
Revises: 
Create Date: 2026-11-26 03:51:16.779918
"""
from alembic import op
import sqlalchemy as sa


revision = '0001_baseline'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Generado con autogenerate y revisado a mano; nombres explicitos = los de PostgreSQL por defecto
    # (identicos a los de la BD de desarrollo creada con create_all).
    op.create_table('roles',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('name', sa.String(length=50), nullable=False),
    sa.Column('description', sa.String(length=200), nullable=True),
    sa.PrimaryKeyConstraint('id', name='roles_pkey')
    )
    op.create_index(op.f('ix_roles_name'), 'roles', ['name'], unique=True)
    op.create_table('users',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('role_id', sa.UUID(), nullable=False),
    sa.Column('username', sa.String(length=255), nullable=False),
    sa.Column('email', sa.String(length=255), nullable=False),
    sa.Column('password_hash', sa.String(length=255), nullable=False),
    sa.Column('full_name', sa.String(length=255), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('created_by', sa.String(length=255), nullable=True),
    sa.ForeignKeyConstraint(['role_id'], ['roles.id'], name='users_role_id_fkey'),
    sa.PrimaryKeyConstraint('id', name='users_pkey')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)
    op.create_table('plots',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('owner_id', sa.UUID(), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('variety', sa.String(length=100), nullable=False),
    sa.Column('area_ha', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('planting_date', sa.Date(), nullable=True),
    sa.Column('plant_count', sa.Integer(), nullable=True),
    sa.Column('notes', sa.String(length=500), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.ForeignKeyConstraint(['owner_id'], ['users.id'], name='plots_owner_id_fkey'),
    sa.PrimaryKeyConstraint('id', name='plots_pkey'),
    sa.UniqueConstraint('owner_id', 'name', name='uq_plots_owner_name')
    )
    op.create_index(op.f('ix_plots_owner_id'), 'plots', ['owner_id'], unique=False)
    op.create_table('user_sessions',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('refresh_token', sa.String(length=255), nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('is_revoked', sa.Boolean(), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='user_sessions_user_id_fkey'),
    sa.PrimaryKeyConstraint('id', name='user_sessions_pkey')
    )
    op.create_index(op.f('ix_user_sessions_refresh_token'), 'user_sessions', ['refresh_token'], unique=True)
    op.create_table('harvests',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('plot_id', sa.UUID(), nullable=False),
    sa.Column('harvested_on', sa.Date(), nullable=False),
    sa.Column('quantity_kg', sa.Numeric(precision=12, scale=2), nullable=False),
    sa.Column('grade', sa.String(length=20), nullable=False),
    sa.Column('notes', sa.String(length=500), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.ForeignKeyConstraint(['plot_id'], ['plots.id'], name='harvests_plot_id_fkey'),
    sa.PrimaryKeyConstraint('id', name='harvests_pkey')
    )
    op.create_index('ix_harvests_plot_date', 'harvests', ['plot_id', 'harvested_on'], unique=False)
    op.create_table('plants',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('plot_id', sa.UUID(), nullable=False),
    sa.Column('row_num', sa.Integer(), nullable=False),
    sa.Column('col_num', sa.Integer(), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.ForeignKeyConstraint(['plot_id'], ['plots.id'], ondelete='CASCADE', name='plants_plot_id_fkey'),
    sa.PrimaryKeyConstraint('id', name='plants_pkey'),
    sa.UniqueConstraint('plot_id', 'row_num', 'col_num', name='uq_plants_position')
    )
    op.create_index(op.f('ix_plants_plot_id'), 'plants', ['plot_id'], unique=False)
    op.create_table('plot_costs',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('plot_id', sa.UUID(), nullable=False),
    sa.Column('incurred_on', sa.Date(), nullable=False),
    sa.Column('category', sa.String(length=20), nullable=False),
    sa.Column('amount', sa.Numeric(precision=14, scale=2), nullable=False),
    sa.Column('notes', sa.String(length=500), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.ForeignKeyConstraint(['plot_id'], ['plots.id'], name='plot_costs_plot_id_fkey'),
    sa.PrimaryKeyConstraint('id', name='plot_costs_pkey')
    )
    op.create_index('ix_plot_costs_plot_date', 'plot_costs', ['plot_id', 'incurred_on'], unique=False)
    op.create_table('plant_observations',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('plant_id', sa.UUID(), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('notes', sa.String(length=500), nullable=True),
    sa.Column('observed_on', sa.Date(), nullable=False),
    sa.Column('recorded_by', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.ForeignKeyConstraint(['plant_id'], ['plants.id'], ondelete='CASCADE', name='plant_observations_plant_id_fkey'),
    sa.ForeignKeyConstraint(['recorded_by'], ['users.id'], name='plant_observations_recorded_by_fkey'),
    sa.PrimaryKeyConstraint('id', name='plant_observations_pkey')
    )
    op.create_index(op.f('ix_plant_observations_plant_id'), 'plant_observations', ['plant_id'], unique=False)


def downgrade() -> None:
    # Orden inverso de dependencias (los indices caen con su tabla; se borran explicitamente por claridad).
    op.drop_index(op.f('ix_plant_observations_plant_id'), table_name='plant_observations')
    op.drop_table('plant_observations')
    op.drop_index('ix_plot_costs_plot_date', table_name='plot_costs')
    op.drop_table('plot_costs')
    op.drop_index(op.f('ix_plants_plot_id'), table_name='plants')
    op.drop_table('plants')
    op.drop_index('ix_harvests_plot_date', table_name='harvests')
    op.drop_table('harvests')
    op.drop_index(op.f('ix_user_sessions_refresh_token'), table_name='user_sessions')
    op.drop_table('user_sessions')
    op.drop_index(op.f('ix_plots_owner_id'), table_name='plots')
    op.drop_table('plots')
    op.drop_index(op.f('ix_users_username'), table_name='users')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
    op.drop_index(op.f('ix_roles_name'), table_name='roles')
    op.drop_table('roles')
