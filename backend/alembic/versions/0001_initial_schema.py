"""Initial schema — baseline snapshot of all tables.

Revision ID: 0001
Revises: (none)
Create Date: 2026-05-31

This migration creates all tables from scratch.  If the database was already
bootstrapped by the old ``Base.metadata.create_all()`` approach (i.e. the tables
already exist), run::

    alembic stamp 0001

…to mark this revision as applied without re-executing the DDL.
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── roles ──────────────────────────────────────────────────────────────────
    op.create_table(
        'roles',
        sa.Column('id', sa.Integer, primary_key=True, index=True),
        sa.Column('name', sa.String, unique=True, index=True),
    )

    # ── instruments ───────────────────────────────────────────────────────────
    op.create_table(
        'instruments',
        sa.Column('id', sa.Integer, primary_key=True, index=True),
        sa.Column('name', sa.String, unique=True, index=True),
    )

    # ── users ─────────────────────────────────────────────────────────────────
    op.create_table(
        'users',
        sa.Column('id', sa.Integer, primary_key=True, index=True),
        sa.Column('email', sa.String, unique=True, index=True),
        sa.Column('name', sa.String),
        sa.Column('hashed_password', sa.String),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('role_id', sa.Integer, sa.ForeignKey('roles.id'), index=True),
        sa.Column('avatar_url', sa.String, nullable=True),
        sa.Column('sessions_left', sa.Integer, default=0, nullable=True),
        sa.Column('username', sa.String, unique=True, index=True, nullable=True),
        sa.Column('contact_number', sa.String, nullable=True),
        sa.Column('home_address', sa.String, nullable=True),
        sa.Column('birthday', sa.String, nullable=True),
        sa.Column('age', sa.Integer, nullable=True),
        sa.Column('school', sa.String, nullable=True),
        sa.Column('parent_name', sa.String, nullable=True),
        sa.Column('parent_contact', sa.String, nullable=True),
        sa.Column('sessions_enrolled', sa.Integer, nullable=True),
        sa.Column('failed_login_count', sa.Integer, nullable=False, server_default='0'),
        sa.Column('locked_until', sa.DateTime, nullable=True),
        sa.Column('email_verified', sa.Boolean, nullable=False, server_default='0'),
        sa.Column('email_verification_token_hash', sa.String, nullable=True),
        sa.Column('totp_secret', sa.String, nullable=True),
        sa.Column('totp_enabled', sa.Boolean, nullable=False, server_default='0'),
        sa.Column('must_change_password', sa.Boolean, nullable=False, server_default='0'),
    )

    # ── user_instruments ──────────────────────────────────────────────────────
    op.create_table(
        'user_instruments',
        sa.Column('user_id', sa.Integer, sa.ForeignKey('users.id'), primary_key=True, index=True),
        sa.Column('instrument_id', sa.Integer, sa.ForeignKey('instruments.id'), primary_key=True, index=True),
    )

    # ── teacher_students ──────────────────────────────────────────────────────
    op.create_table(
        'teacher_students',
        sa.Column('id', sa.Integer, primary_key=True, index=True),
        sa.Column('teacher_id', sa.Integer, sa.ForeignKey('users.id'), index=True),
        sa.Column('student_id', sa.Integer, sa.ForeignKey('users.id'), index=True),
        sa.Column('assigned_at', sa.DateTime),
    )

    # ── sessions ──────────────────────────────────────────────────────────────
    op.create_table(
        'sessions',
        sa.Column('id', sa.Integer, primary_key=True, index=True),
        sa.Column('teacher_id', sa.Integer, sa.ForeignKey('users.id'), index=True),
        sa.Column('student_id', sa.Integer, sa.ForeignKey('users.id'), index=True),
        sa.Column('start_time', sa.DateTime, index=True),
        sa.Column('end_time', sa.DateTime),
        sa.Column('status', sa.String, default='scheduled', index=True),
        sa.Column('proposed_by', sa.Integer, sa.ForeignKey('users.id'), nullable=True, index=True),
        sa.Column('notes', sa.String, nullable=True),
        sa.Column('instrument_id', sa.Integer, sa.ForeignKey('instruments.id'), nullable=True, index=True),
        sa.Column('is_manual_entry', sa.Boolean, default=False),
        sa.Column('session_number', sa.Integer, nullable=True),
        sa.Column('notified_24h', sa.Boolean, default=False),
        sa.Column('notified_12h', sa.Boolean, default=False),
        sa.Column('stale_reminded_at', sa.DateTime, nullable=True),
        sa.Column('proof_justification', sa.String, nullable=True),
        sa.Column('rejection_reason', sa.String, nullable=True),
        sa.Column('is_force_completed', sa.Boolean, default=False),
        sa.Column('created_at', sa.DateTime),
        sa.Column('updated_at', sa.DateTime),
        sa.Column('counter_count', sa.Integer, default=0, server_default='0'),
        sa.Column('version', sa.Integer, nullable=False, server_default='0'),
    )

    # ── enrollments ───────────────────────────────────────────────────────────
    op.create_table(
        'enrollments',
        sa.Column('id', sa.Integer, primary_key=True, index=True),
        sa.Column('student_id', sa.Integer, sa.ForeignKey('users.id'), index=True),
        sa.Column('teacher_id', sa.Integer, sa.ForeignKey('users.id'), index=True),
        sa.Column('sessions_purchased', sa.Integer, default=0),
        sa.Column('sessions_used', sa.Integer, default=0),
        sa.Column('created_at', sa.DateTime),
    )

    # ── homework ──────────────────────────────────────────────────────────────
    op.create_table(
        'homework',
        sa.Column('id', sa.Integer, primary_key=True, index=True),
        sa.Column('session_id', sa.Integer, sa.ForeignKey('sessions.id'), index=True),
        sa.Column('description', sa.String),
        sa.Column('is_completed', sa.Boolean, default=False),
        sa.Column('file_url', sa.String, nullable=True),
        sa.Column('created_at', sa.DateTime),
    )

    # ── session_proofs ────────────────────────────────────────────────────────
    op.create_table(
        'session_proofs',
        sa.Column('id', sa.Integer, primary_key=True, index=True),
        sa.Column('session_id', sa.Integer, sa.ForeignKey('sessions.id'), index=True),
        sa.Column('image_url', sa.String),
        sa.Column('uploaded_at', sa.DateTime),
        sa.Column('uploader_id', sa.Integer, sa.ForeignKey('users.id'), nullable=True, index=True),
        sa.Column('uploader_role', sa.String, nullable=True),
    )

    # ── payments ──────────────────────────────────────────────────────────────
    op.create_table(
        'payments',
        sa.Column('id', sa.Integer, primary_key=True, index=True),
        sa.Column('student_id', sa.Integer, sa.ForeignKey('users.id'), index=True),
        sa.Column('amount', sa.Integer),
        sa.Column('date', sa.DateTime),
        sa.Column('method', sa.String),
        sa.Column('status', sa.String, default='completed'),
        sa.Column('notes', sa.String, nullable=True),
    )

    # ── notifications ─────────────────────────────────────────────────────────
    op.create_table(
        'notifications',
        sa.Column('id', sa.Integer, primary_key=True, index=True),
        sa.Column('user_id', sa.Integer, sa.ForeignKey('users.id'), index=True),
        sa.Column('message', sa.String),
        sa.Column('link', sa.String, nullable=True),
        sa.Column('is_read', sa.Boolean, default=False),
        sa.Column('created_at', sa.DateTime),
    )
    op.create_index('ix_notifications_user_unread', 'notifications', ['user_id', 'is_read'])

    # ── instrument_products ───────────────────────────────────────────────────
    op.create_table(
        'instrument_products',
        sa.Column('id', sa.Integer, primary_key=True, index=True),
        sa.Column('name', sa.String, nullable=False, index=True),
        sa.Column('description', sa.String, nullable=True),
        sa.Column('price_cents', sa.Integer, nullable=False, default=0),
        sa.Column('stock', sa.Integer, nullable=False, default=0),
        sa.Column('image_url', sa.String, nullable=True),
        sa.Column('category_id', sa.Integer, sa.ForeignKey('instruments.id'), nullable=True, index=True),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('created_at', sa.DateTime),
        sa.Column('updated_at', sa.DateTime),
    )

    # ── orders ────────────────────────────────────────────────────────────────
    op.create_table(
        'orders',
        sa.Column('id', sa.Integer, primary_key=True, index=True),
        sa.Column('user_id', sa.Integer, sa.ForeignKey('users.id'), nullable=False, index=True),
        sa.Column('status', sa.String, nullable=False, default='pending', index=True),
        sa.Column('notes', sa.String, nullable=True),
        sa.Column('total_cents', sa.Integer, nullable=False, default=0),
        sa.Column('approved_by', sa.Integer, sa.ForeignKey('users.id'), nullable=True, index=True),
        sa.Column('approved_at', sa.DateTime, nullable=True),
        sa.Column('rejection_reason', sa.String, nullable=True),
        sa.Column('created_at', sa.DateTime, index=True),
        sa.Column('updated_at', sa.DateTime),
    )

    # ── order_items ───────────────────────────────────────────────────────────
    op.create_table(
        'order_items',
        sa.Column('id', sa.Integer, primary_key=True, index=True),
        sa.Column('order_id', sa.Integer, sa.ForeignKey('orders.id'), nullable=False, index=True),
        sa.Column('product_id', sa.Integer, sa.ForeignKey('instrument_products.id'), nullable=False, index=True),
        sa.Column('quantity', sa.Integer, nullable=False, default=1),
        sa.Column('price_cents_at_purchase', sa.Integer, nullable=False),
    )

    # ── conversations ─────────────────────────────────────────────────────────
    op.create_table(
        'conversations',
        sa.Column('id', sa.Integer, primary_key=True, index=True),
        sa.Column('type', sa.String, nullable=False, default='dm'),
        sa.Column('name', sa.String, nullable=True),
        sa.Column('created_at', sa.DateTime),
    )

    # ── conversation_participants ─────────────────────────────────────────────
    op.create_table(
        'conversation_participants',
        sa.Column('id', sa.Integer, primary_key=True, index=True),
        sa.Column('conversation_id', sa.Integer, sa.ForeignKey('conversations.id'), nullable=False, index=True),
        sa.Column('user_id', sa.Integer, sa.ForeignKey('users.id'), nullable=False, index=True),
        sa.Column('joined_at', sa.DateTime),
        sa.Column('last_read_at', sa.DateTime, nullable=True),
        sa.UniqueConstraint('conversation_id', 'user_id', name='uq_conv_participant'),
    )

    # ── messages ──────────────────────────────────────────────────────────────
    op.create_table(
        'messages',
        sa.Column('id', sa.Integer, primary_key=True, index=True),
        sa.Column('conversation_id', sa.Integer, sa.ForeignKey('conversations.id'), nullable=False, index=True),
        sa.Column('sender_id', sa.Integer, sa.ForeignKey('users.id'), nullable=False, index=True),
        sa.Column('body', sa.String, nullable=False),
        sa.Column('created_at', sa.DateTime, index=True),
        sa.Column('is_deleted', sa.Boolean, default=False),
    )

    # ── session_threads ───────────────────────────────────────────────────────
    op.create_table(
        'session_threads',
        sa.Column('id', sa.Integer, primary_key=True, index=True),
        sa.Column('session_id', sa.Integer, sa.ForeignKey('sessions.id'), unique=True, nullable=False),
        sa.Column('conversation_id', sa.Integer, sa.ForeignKey('conversations.id'), unique=True, nullable=False),
    )

    # ── activity_logs ─────────────────────────────────────────────────────────
    op.create_table(
        'activity_logs',
        sa.Column('id', sa.Integer, primary_key=True, index=True),
        sa.Column('action_type', sa.String, nullable=False, index=True),
        sa.Column('actor_id', sa.Integer, sa.ForeignKey('users.id'), nullable=True, index=True),
        sa.Column('actor_name', sa.String, nullable=True),
        sa.Column('target_type', sa.String, nullable=True),
        sa.Column('target_id', sa.Integer, nullable=True),
        sa.Column('description', sa.String, nullable=False),
        sa.Column('created_at', sa.DateTime, index=True),
    )

    # ── refresh_tokens ────────────────────────────────────────────────────────
    op.create_table(
        'refresh_tokens',
        sa.Column('id', sa.Integer, primary_key=True, index=True),
        sa.Column('user_id', sa.Integer, sa.ForeignKey('users.id'), nullable=False, index=True),
        sa.Column('token_hash', sa.String, nullable=False, unique=True, index=True),
        sa.Column('expires_at', sa.DateTime, nullable=False),
        sa.Column('revoked', sa.Boolean, nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('last_used_at', sa.DateTime, nullable=True),
    )

    # ── password_reset_tokens ─────────────────────────────────────────────────
    op.create_table(
        'password_reset_tokens',
        sa.Column('id', sa.Integer, primary_key=True, index=True),
        sa.Column('user_id', sa.Integer, sa.ForeignKey('users.id'), nullable=False, index=True),
        sa.Column('token_hash', sa.String, nullable=False, unique=True, index=True),
        sa.Column('expires_at', sa.DateTime, nullable=False),
        sa.Column('used_at', sa.DateTime, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False),
    )

    # ── push_subscriptions ────────────────────────────────────────────────────
    op.create_table(
        'push_subscriptions',
        sa.Column('id', sa.Integer, primary_key=True, index=True),
        sa.Column('user_id', sa.Integer, sa.ForeignKey('users.id'), nullable=False, index=True),
        sa.Column('endpoint', sa.String, nullable=False, unique=True, index=True),
        sa.Column('keys_p256dh', sa.String, nullable=False),
        sa.Column('keys_auth', sa.String, nullable=False),
        sa.Column('user_agent', sa.String, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False),
    )


def downgrade() -> None:
    op.drop_table('push_subscriptions')
    op.drop_table('password_reset_tokens')
    op.drop_table('refresh_tokens')
    op.drop_table('activity_logs')
    op.drop_table('session_threads')
    op.drop_table('messages')
    op.drop_table('conversation_participants')
    op.drop_table('conversations')
    op.drop_table('order_items')
    op.drop_table('orders')
    op.drop_table('instrument_products')
    op.drop_index('ix_notifications_user_unread', table_name='notifications')
    op.drop_table('notifications')
    op.drop_table('payments')
    op.drop_table('session_proofs')
    op.drop_table('homework')
    op.drop_table('enrollments')
    op.drop_table('sessions')
    op.drop_table('teacher_students')
    op.drop_table('user_instruments')
    op.drop_table('users')
    op.drop_table('instruments')
    op.drop_table('roles')
