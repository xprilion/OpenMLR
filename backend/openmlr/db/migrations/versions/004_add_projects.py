"""Add projects table and project_id to conversations

Revision ID: 004_add_projects
Revises: 003_migrate_sandbox_to_compute
Create Date: 2026-04-27
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '004_add_projects'
down_revision: Union[str, None] = '003_migrate_sandbox_to_compute'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create projects table
    op.create_table(
        'projects',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('uuid', sa.String(36), unique=True, nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('slug', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('workspace_path', sa.String(1000), nullable=True),
        sa.Column('status', sa.String(20), server_default='active', nullable=False),
        sa.Column('settings', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_projects_user_id', 'projects', ['user_id'])
    op.create_unique_constraint('uq_projects_user_slug', 'projects', ['user_id', 'slug'])

    # Add project_id column to conversations
    op.add_column(
        'conversations',
        sa.Column('project_id', sa.Integer(), sa.ForeignKey('projects.id', ondelete='SET NULL'), nullable=True),
    )
    op.create_index('ix_conversations_project_id', 'conversations', ['project_id'])


def downgrade() -> None:
    op.drop_index('ix_conversations_project_id', table_name='conversations')
    op.drop_column('conversations', 'project_id')
    op.drop_table('projects')
