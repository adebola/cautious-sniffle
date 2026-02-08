"""Repository for Notification CRUD operations."""

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification


class NotificationRepository:
    """Data-access layer for the notifications table."""

    async def list_by_user(
        self,
        session: AsyncSession,
        user_id: UUID,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Notification], int]:
        """List notifications for a user with pagination.

        Returns a tuple of (notifications, total_count), ordered by
        created_at descending (newest first).
        """
        base = select(Notification).where(Notification.user_id == user_id)

        # Total count
        count_stmt = select(func.count()).select_from(base.subquery())
        total_result = await session.execute(count_stmt)
        total = total_result.scalar() or 0

        # Ordering and pagination
        offset = (page - 1) * page_size
        base = base.order_by(Notification.created_at.desc())
        base = base.offset(offset).limit(page_size)

        result = await session.execute(base)
        notifications = list(result.scalars().all())
        return notifications, total

    async def get_unread_count(self, session: AsyncSession, user_id: UUID) -> int:
        """Return the number of unread notifications for a user."""
        stmt = (
            select(func.count())
            .select_from(Notification)
            .where(
                Notification.user_id == user_id,
                Notification.read_at.is_(None),
            )
        )
        result = await session.execute(stmt)
        return result.scalar() or 0

    async def get_by_id(
        self,
        session: AsyncSession,
        notification_id: UUID,
        user_id: UUID,
    ) -> Notification | None:
        """Fetch a notification by ID, scoped to a specific user."""
        stmt = select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == user_id,
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def mark_read(
        self,
        session: AsyncSession,
        notification_id: UUID,
        user_id: UUID,
    ) -> Notification | None:
        """Mark a single notification as read. Returns the updated notification or None."""
        now = datetime.now(timezone.utc)
        stmt = (
            update(Notification)
            .where(
                Notification.id == notification_id,
                Notification.user_id == user_id,
            )
            .values(read_at=now)
            .returning(Notification)
        )
        result = await session.execute(stmt)
        await session.flush()
        row = result.scalar_one_or_none()
        return row

    async def mark_all_read(self, session: AsyncSession, user_id: UUID) -> int:
        """Mark all unread notifications as read for a user. Returns count of updated rows."""
        now = datetime.now(timezone.utc)
        stmt = (
            update(Notification)
            .where(
                Notification.user_id == user_id,
                Notification.read_at.is_(None),
            )
            .values(read_at=now)
        )
        result = await session.execute(stmt)
        await session.flush()
        return result.rowcount

    async def create(self, session: AsyncSession, notification: Notification) -> Notification:
        """Insert a new notification record."""
        session.add(notification)
        await session.flush()
        await session.refresh(notification)
        return notification

    async def delete(
        self,
        session: AsyncSession,
        notification_id: UUID,
        user_id: UUID,
    ) -> bool:
        """Delete a notification by ID, scoped to a specific user. Returns True if deleted."""
        stmt = delete(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == user_id,
        )
        result = await session.execute(stmt)
        await session.flush()
        return result.rowcount > 0
