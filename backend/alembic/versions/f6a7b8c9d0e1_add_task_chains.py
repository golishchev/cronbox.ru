"""add_task_chains

Add Task Chains feature with chains, steps, and execution tracking.

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-01-16 15:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'f6a7b8c9d0e1'
down_revision: Union[str, Sequence[str], None] = 'e5f6a7b8c9d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add task chains tables and related columns."""
    # Create enums using raw SQL with IF NOT EXISTS (checkfirst doesn't work with asyncpg)
    # Models use create_type=False to prevent duplicate creation
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'triggertype') THEN
                CREATE TYPE triggertype AS ENUM ('cron', 'delayed', 'manual');
            END IF;
        END
        $$;
    """)

    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'chainstatus') THEN
                CREATE TYPE chainstatus AS ENUM ('pending', 'running', 'success', 'failed', 'partial', 'cancelled');
            END IF;
        END
        $$;
    """)

    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'stepstatus') THEN
                CREATE TYPE stepstatus AS ENUM ('pending', 'running', 'success', 'failed', 'skipped');
            END IF;
        END
        $$;
    """)

    # Create task_chains table
    op.create_table(
        'task_chains',
        sa.Column('workspace_id', sa.UUID(), nullable=False),
        sa.Column('worker_id', sa.UUID(), nullable=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('tags', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('trigger_type', postgresql.ENUM('cron', 'delayed', 'manual', name='triggertype', create_type=False), nullable=False, server_default='manual'),
        sa.Column('schedule', sa.String(length=100), nullable=True),
        sa.Column('timezone', sa.String(length=50), nullable=False, server_default='Europe/Moscow'),
        sa.Column('execute_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('stop_on_failure', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('timeout_seconds', sa.Integer(), nullable=False, server_default='300'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_paused', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('last_run_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_status', postgresql.ENUM('pending', 'running', 'success', 'failed', 'partial', 'cancelled', name='chainstatus', create_type=False), nullable=True),
        sa.Column('next_run_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('consecutive_failures', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('notify_on_failure', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('notify_on_success', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('notify_on_partial', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['worker_id'], ['workers.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_task_chains_workspace_id', 'task_chains', ['workspace_id'], unique=False)
    op.create_index('ix_task_chains_worker_id', 'task_chains', ['worker_id'], unique=False)
    op.create_index('ix_task_chains_is_active', 'task_chains', ['is_active'], unique=False)
    op.create_index('ix_task_chains_next_run_at', 'task_chains', ['next_run_at'], unique=False)

    # Create chain_steps table
    op.create_table(
        'chain_steps',
        sa.Column('chain_id', sa.UUID(), nullable=False),
        sa.Column('step_order', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('url', sa.String(length=2048), nullable=False),
        sa.Column('method', postgresql.ENUM('GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD', name='httpmethod', create_type=False), nullable=False, server_default='GET'),
        sa.Column('headers', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('body', sa.Text(), nullable=True),
        sa.Column('timeout_seconds', sa.Integer(), nullable=False, server_default='30'),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('retry_delay_seconds', sa.Integer(), nullable=False, server_default='5'),
        sa.Column('condition', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('extract_variables', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('continue_on_failure', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['chain_id'], ['task_chains.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_chain_steps_chain_id', 'chain_steps', ['chain_id'], unique=False)

    # Create chain_executions table
    op.create_table(
        'chain_executions',
        sa.Column('workspace_id', sa.UUID(), nullable=False),
        sa.Column('chain_id', sa.UUID(), nullable=False),
        sa.Column('status', postgresql.ENUM('pending', 'running', 'success', 'failed', 'partial', 'cancelled', name='chainstatus', create_type=False), nullable=False, server_default='pending'),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('total_steps', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('completed_steps', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('failed_steps', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('skipped_steps', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('variables', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['chain_id'], ['task_chains.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_chain_executions_workspace_id', 'chain_executions', ['workspace_id'], unique=False)
    op.create_index('ix_chain_executions_chain_id', 'chain_executions', ['chain_id'], unique=False)

    # Create step_executions table
    op.create_table(
        'step_executions',
        sa.Column('chain_execution_id', sa.UUID(), nullable=False),
        sa.Column('step_id', sa.UUID(), nullable=True),
        sa.Column('step_order', sa.Integer(), nullable=False),
        sa.Column('step_name', sa.String(length=255), nullable=False),
        sa.Column('status', postgresql.ENUM('pending', 'running', 'success', 'failed', 'skipped', name='stepstatus', create_type=False), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('retry_attempt', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('request_url', sa.String(length=2048), nullable=False),
        sa.Column('request_method', postgresql.ENUM('GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD', name='httpmethod', create_type=False), nullable=False),
        sa.Column('request_headers', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('request_body', sa.Text(), nullable=True),
        sa.Column('response_status_code', sa.Integer(), nullable=True),
        sa.Column('response_headers', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('response_body', sa.Text(), nullable=True),
        sa.Column('response_size_bytes', sa.Integer(), nullable=True),
        sa.Column('extracted_variables', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('condition_met', sa.Boolean(), nullable=True),
        sa.Column('condition_details', sa.Text(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('error_type', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(['chain_execution_id'], ['chain_executions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['step_id'], ['chain_steps.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_step_executions_chain_execution_id', 'step_executions', ['chain_execution_id'], unique=False)
    op.create_index('ix_step_executions_step_id', 'step_executions', ['step_id'], unique=False)

    # Add task_chains_count to workspaces
    op.add_column('workspaces', sa.Column('task_chains_count', sa.Integer(), nullable=False, server_default='0'))

    # Add task chain limits to plans
    op.add_column('plans', sa.Column('max_task_chains', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('plans', sa.Column('max_chain_steps', sa.Integer(), nullable=False, server_default='5'))
    op.add_column('plans', sa.Column('chain_variable_substitution', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('plans', sa.Column('min_chain_interval_minutes', sa.Integer(), nullable=False, server_default='15'))


def downgrade() -> None:
    """Remove task chains tables and related columns."""
    # Remove columns from plans
    op.drop_column('plans', 'min_chain_interval_minutes')
    op.drop_column('plans', 'chain_variable_substitution')
    op.drop_column('plans', 'max_chain_steps')
    op.drop_column('plans', 'max_task_chains')

    # Remove column from workspaces
    op.drop_column('workspaces', 'task_chains_count')

    # Drop step_executions table
    op.drop_index('ix_step_executions_step_id', table_name='step_executions')
    op.drop_index('ix_step_executions_chain_execution_id', table_name='step_executions')
    op.drop_table('step_executions')

    # Drop chain_executions table
    op.drop_index('ix_chain_executions_chain_id', table_name='chain_executions')
    op.drop_index('ix_chain_executions_workspace_id', table_name='chain_executions')
    op.drop_table('chain_executions')

    # Drop chain_steps table
    op.drop_index('ix_chain_steps_chain_id', table_name='chain_steps')
    op.drop_table('chain_steps')

    # Drop task_chains table
    op.drop_index('ix_task_chains_next_run_at', table_name='task_chains')
    op.drop_index('ix_task_chains_is_active', table_name='task_chains')
    op.drop_index('ix_task_chains_worker_id', table_name='task_chains')
    op.drop_index('ix_task_chains_workspace_id', table_name='task_chains')
    op.drop_table('task_chains')

    # Drop enums
    op.execute("DROP TYPE IF EXISTS stepstatus")
    op.execute("DROP TYPE IF EXISTS chainstatus")
    op.execute("DROP TYPE IF EXISTS triggertype")
