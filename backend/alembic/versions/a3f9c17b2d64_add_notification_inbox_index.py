"""add notification inbox index

Revision ID: a3f9c17b2d64
Revises: fcf7da7aa9a0
Create Date: 2026-09-25 10:14:22.108455

Supports the notification inbox query in ``Notification.latest``, which scopes
by ``user_id`` and orders by ``created_at DESC, id DESC``. The existing
``ix_notifications_user_status (user_id, is_read)`` cannot serve that sort.
PostgreSQL scans this index backwards to satisfy the descending order.
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'a3f9c17b2d64'
down_revision: Union[str, None] = 'fcf7da7aa9a0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        'ix_notifications_user_created',
        'notifications',
        ['user_id', 'created_at', 'id'],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index('ix_notifications_user_created', table_name='notifications')
