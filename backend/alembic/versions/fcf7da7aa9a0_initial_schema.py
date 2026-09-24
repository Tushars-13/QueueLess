"""initial schema

Revision ID: fcf7da7aa9a0
Revises:
Create Date: 2026-09-06 19:01:13.646364

This migration creates the full QueueLess MVP schema per docs/database-design.md:

  users, businesses, business_photos, business_hours, services, staff,
  staff_services, daily_queues, queue_entries, queue_events, notifications

It also creates the four PostgreSQL ENUM types:
  user_role, daily_queue_status, queue_entry_status, notification_type
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fcf7da7aa9a0'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# All table PKs are BIGINT (BIGSERIAL) per database-design.md.

def upgrade() -> None:
    # --- Enumerated types ---------------------------------------------------
    user_role = sa.Enum(
        'CUSTOMER', 'BUSINESS_OWNER', name='user_role'
    )
    daily_queue_status = sa.Enum(
        'OPEN', 'CLOSED', name='daily_queue_status'
    )
    queue_entry_status = sa.Enum(
        'REQUESTED', 'ACCEPTED', 'WAITING', 'CALLED', 'IN_SERVICE',
        'COMPLETED', 'REJECTED', 'CANCELLED', 'SKIPPED', 'NO_SHOW',
        name='queue_entry_status',
    )
    notification_type = sa.Enum(
        'QUEUE_ACCEPTED', 'REQUEST_REJECTED', 'TURN_APPROACHING',
        'TURN_REACHED', 'QUEUE_CLOSED', 'GENERAL',
        name='notification_type',
    )

    # --- users --------------------------------------------------------------
    op.create_table(
        'users',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('email', sa.String(length=254), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=False),
        sa.Column('phone', sa.String(length=32), nullable=True),
        sa.Column(
            'role',
            user_role,
            nullable=False,
        ),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_users')),
        sa.UniqueConstraint('email', name=op.f('uq_users_email')),
    )

    # --- businesses ----------------------------------------------------------
    op.create_table(
        'businesses',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('owner_id', sa.BigInteger(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('category', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('address', sa.String(length=255), nullable=True),
        sa.Column('latitude', sa.Numeric(9, 6), nullable=True),
        sa.Column('longitude', sa.Numeric(9, 6), nullable=True),
        sa.Column('timezone', sa.String(length=64), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ['owner_id'],
            ['users.id'],
            name=op.f('fk_businesses_owner_id_users'),
            ondelete='RESTRICT',
        ),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_businesses')),
    )
    op.create_index(
        'ix_businesses_category', 'businesses', ['category'], unique=False
    )
    op.create_index(
        'ix_businesses_owner_id', 'businesses', ['owner_id'], unique=False
    )

    # --- business_photos -----------------------------------------------------
    op.create_table(
        'business_photos',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('business_id', sa.BigInteger(), nullable=False),
        sa.Column('photo_url', sa.String(length=500), nullable=False),
        sa.Column('position', sa.SmallInteger(), nullable=False),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ['business_id'],
            ['businesses.id'],
            name=op.f('fk_business_photos_business_id_businesses'),
            ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_business_photos')),
    )

    # --- business_hours ------------------------------------------------------
    op.create_table(
        'business_hours',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('business_id', sa.BigInteger(), nullable=False),
        sa.Column('day_of_week', sa.SmallInteger(), nullable=False),
        sa.Column('open_time', sa.Time(), nullable=True),
        sa.Column('close_time', sa.Time(), nullable=True),
        sa.Column('is_closed', sa.Boolean(), nullable=False),
        sa.CheckConstraint(
            'day_of_week BETWEEN 0 AND 6',
            name=op.f('ck_business_hours_day_of_week_range'),
        ),
        sa.ForeignKeyConstraint(
            ['business_id'],
            ['businesses.id'],
            name=op.f('fk_business_hours_business_id_businesses'),
            ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_business_hours')),
        sa.UniqueConstraint(
            'business_id',
            'day_of_week',
            name=op.f('uq_business_hours_business_day'),
        ),
    )

    # --- services ------------------------------------------------------------
    op.create_table(
        'services',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('business_id', sa.BigInteger(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('price', sa.Numeric(10, 2), nullable=True),
        sa.Column('duration_minutes', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ['business_id'],
            ['businesses.id'],
            name=op.f('fk_services_business_id_businesses'),
            ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_services')),
        sa.UniqueConstraint(
            'business_id', 'name', name=op.f('uq_services_business_name')
        ),
    )

    # --- staff ---------------------------------------------------------------
    op.create_table(
        'staff',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('business_id', sa.BigInteger(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=True),
        sa.Column('available', sa.Boolean(), nullable=False),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ['business_id'],
            ['businesses.id'],
            name=op.f('fk_staff_business_id_businesses'),
            ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_staff')),
        sa.UniqueConstraint(
            'business_id', 'name', name=op.f('uq_staff_business_name')
        ),
    )

    # --- daily_queues --------------------------------------------------------
    op.create_table(
        'daily_queues',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('business_id', sa.BigInteger(), nullable=False),
        sa.Column('queue_date', sa.Date(), nullable=False),
        sa.Column(
            'status',
            daily_queue_status,
            nullable=False,
        ),
        sa.Column('last_token', sa.BigInteger(), nullable=False),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ['business_id'],
            ['businesses.id'],
            name=op.f('fk_daily_queues_business_id_businesses'),
            ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_daily_queues')),
        sa.UniqueConstraint(
            'business_id',
            'queue_date',
            name=op.f('uq_daily_queues_business_date'),
        ),
    )
    op.create_index(
        'ix_daily_queues_business_id',
        'daily_queues',
        ['business_id'],
        unique=False,
    )

    # --- queue_entries -------------------------------------------------------
    op.create_table(
        'queue_entries',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('daily_queue_id', sa.BigInteger(), nullable=False),
        sa.Column('customer_id', sa.BigInteger(), nullable=False),
        sa.Column('service_id', sa.BigInteger(), nullable=False),
        sa.Column('staff_id', sa.BigInteger(), nullable=True),
        sa.Column(
            'status',
            queue_entry_status,
            nullable=False,
        ),
        sa.Column('token_number', sa.BigInteger(), nullable=True),
        sa.Column(
            'requested_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.Column('accepted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ['customer_id'],
            ['users.id'],
            name=op.f('fk_queue_entries_customer_id_users'),
            ondelete='RESTRICT',
        ),
        sa.ForeignKeyConstraint(
            ['daily_queue_id'],
            ['daily_queues.id'],
            name=op.f('fk_queue_entries_daily_queue_id_daily_queues'),
            ondelete='CASCADE',
        ),
        sa.ForeignKeyConstraint(
            ['service_id'],
            ['services.id'],
            name=op.f('fk_queue_entries_service_id_services'),
            ondelete='RESTRICT',
        ),
        sa.ForeignKeyConstraint(
            ['staff_id'],
            ['staff.id'],
            name=op.f('fk_queue_entries_staff_id_staff'),
            ondelete='RESTRICT',
        ),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_queue_entries')),
    )
    op.create_index(
        'ix_queue_entries_customer_id',
        'queue_entries',
        ['customer_id'],
        unique=False,
    )
    op.create_index(
        'ix_queue_entries_daily_queue_id',
        'queue_entries',
        ['daily_queue_id'],
        unique=False,
    )
    op.create_index(
        'ix_queue_entries_service_id',
        'queue_entries',
        ['service_id'],
        unique=False,
    )
    op.create_index(
        'ix_queue_entries_status',
        'queue_entries',
        ['status'],
        unique=False,
    )
    op.create_index(
        'ix_queue_entries_staff_id',
        'queue_entries',
        ['staff_id'],
        unique=False,
    )
    # FIFO ordering + position scans.
    op.create_index(
        'ix_queue_entries_fifo',
        'queue_entries',
        ['daily_queue_id', 'staff_id', 'accepted_at', 'id'],
        unique=False,
    )
    # Token must be unique within a daily queue (only for issued tokens).
    op.create_index(
        'uq_queue_entries_token',
        'queue_entries',
        ['daily_queue_id', 'token_number'],
        unique=True,
        postgresql_where=sa.text('token_number IS NOT NULL'),
    )
    # A customer cannot be active in the same daily queue more than once.
    op.create_index(
        'uq_queue_entries_customer_active',
        'queue_entries',
        ['customer_id', 'daily_queue_id'],
        unique=True,
        postgresql_where=sa.text(
            "status IN ('REQUESTED', 'ACCEPTED', 'WAITING', "
            "'CALLED', 'IN_SERVICE')"
        ),
    )

    # --- staff_services ------------------------------------------------------
    op.create_table(
        'staff_services',
        sa.Column('staff_id', sa.BigInteger(), nullable=False),
        sa.Column('service_id', sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(
            ['service_id'],
            ['services.id'],
            name=op.f('fk_staff_services_service_id_services'),
            ondelete='CASCADE',
        ),
        sa.ForeignKeyConstraint(
            ['staff_id'],
            ['staff.id'],
            name=op.f('fk_staff_services_staff_id_staff'),
            ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint(
            'staff_id', 'service_id', name=op.f('pk_staff_services')
        ),
    )

    # --- notifications -------------------------------------------------------
    op.create_table(
        'notifications',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column(
            'type',
            notification_type,
            nullable=False,
        ),
        sa.Column('queue_entry_id', sa.BigInteger(), nullable=True),
        sa.Column('is_read', sa.Boolean(), nullable=False),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ['queue_entry_id'],
            ['queue_entries.id'],
            name=op.f('fk_notifications_queue_entry_id_queue_entries'),
            ondelete='SET NULL',
        ),
        sa.ForeignKeyConstraint(
            ['user_id'],
            ['users.id'],
            name=op.f('fk_notifications_user_id_users'),
            ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_notifications')),
    )
    op.create_index(
        'ix_notifications_user_id',
        'notifications',
        ['user_id'],
        unique=False,
    )

    # --- queue_events --------------------------------------------------------
    op.create_table(
        'queue_events',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('queue_entry_id', sa.BigInteger(), nullable=False),
        sa.Column('business_id', sa.BigInteger(), nullable=False),
        sa.Column('from_status', queue_entry_status, nullable=True),
        sa.Column('to_status', queue_entry_status, nullable=False),
        sa.Column('actor_id', sa.BigInteger(), nullable=True),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ['actor_id'],
            ['users.id'],
            name=op.f('fk_queue_events_actor_id_users'),
            ondelete='SET NULL',
        ),
        sa.ForeignKeyConstraint(
            ['business_id'],
            ['businesses.id'],
            name=op.f('fk_queue_events_business_id_businesses'),
            ondelete='RESTRICT',
        ),
        sa.ForeignKeyConstraint(
            ['queue_entry_id'],
            ['queue_entries.id'],
            name=op.f('fk_queue_events_queue_entry_id_queue_entries'),
            ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_queue_events')),
    )
    op.create_index(
        'ix_queue_events_created_at',
        'queue_events',
        ['created_at'],
        unique=False,
    )
    # Analytics: peak hours and daily counts by business.
    op.create_index(
        'ix_queue_events_business_time',
        'queue_events',
        ['business_id', 'created_at'],
        unique=False,
    )


def downgrade() -> None:
    # Drop reverse-order (children before parents).
    op.drop_index('ix_queue_events_business_time', table_name='queue_events')
    op.drop_index('ix_queue_events_created_at', table_name='queue_events')
    op.drop_table('queue_events')

    op.drop_index('ix_notifications_user_id', table_name='notifications')
    op.drop_table('notifications')

    op.drop_table('staff_services')

    op.drop_index('uq_queue_entries_customer_active', table_name='queue_entries')
    op.drop_index('uq_queue_entries_token', table_name='queue_entries')
    op.drop_index('ix_queue_entries_fifo', table_name='queue_entries')
    op.drop_index('ix_queue_entries_staff_id', table_name='queue_entries')
    op.drop_index('ix_queue_entries_status', table_name='queue_entries')
    op.drop_index('ix_queue_entries_service_id', table_name='queue_entries')
    op.drop_index('ix_queue_entries_daily_queue_id', table_name='queue_entries')
    op.drop_index('ix_queue_entries_customer_id', table_name='queue_entries')
    op.drop_table('queue_entries')

    op.drop_index('ix_daily_queues_business_id', table_name='daily_queues')
    op.drop_table('daily_queues')

    op.drop_table('staff')

    op.drop_table('services')

    op.drop_table('business_hours')

    op.drop_table('business_photos')

    op.drop_index('ix_businesses_owner_id', table_name='businesses')
    op.drop_index('ix_businesses_category', table_name='businesses')
    op.drop_table('businesses')

    op.drop_index('ix_users_email', table_name='users')
    op.drop_table('users')

    # --- Enumerated types ---------------------------------------------------
    notification_type = sa.Enum(name='notification_type')
    notification_type.drop(op.get_bind(), checkfirst=True)
    queue_entry_status = sa.Enum(name='queue_entry_status')
    queue_entry_status.drop(op.get_bind(), checkfirst=True)
    daily_queue_status = sa.Enum(name='daily_queue_status')
    daily_queue_status.drop(op.get_bind(), checkfirst=True)
    user_role = sa.Enum(name='user_role')
    user_role.drop(op.get_bind(), checkfirst=True)