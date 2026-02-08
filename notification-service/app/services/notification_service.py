"""Notification business logic."""

import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from chatcraft_common.errors import NotFoundException
from chatcraft_common.pagination import PaginatedResponse

from app.models.notification import Notification
from app.repositories.notification_repository import NotificationRepository
from app.schemas.notification import NotificationCreate, NotificationResponse

logger = logging.getLogger(__name__)

# Error code for notification-specific errors
NOTIF_NOT_FOUND = "NOTIF_001"


class NotificationService:
    """Service layer for managing in-app notifications."""

    def __init__(self, notification_repo: NotificationRepository) -> None:
        self._notification_repo = notification_repo

    async def list_notifications(
        self,
        session: AsyncSession,
        user_id: UUID,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedResponse:
        """Return a paginated list of notifications for a user."""
        notifications, total = await self._notification_repo.list_by_user(
            session,
            user_id=user_id,
            page=page,
            page_size=page_size,
        )

        items = [
            NotificationResponse.model_validate(n).model_dump(mode="json")
            for n in notifications
        ]
        return PaginatedResponse.create(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
        )

    async def get_unread_count(self, session: AsyncSession, user_id: UUID) -> int:
        """Return the number of unread notifications for a user."""
        return await self._notification_repo.get_unread_count(session, user_id)

    async def mark_read(
        self,
        session: AsyncSession,
        notification_id: UUID,
        user_id: UUID,
    ) -> Notification:
        """Mark a single notification as read.

        Raises NotFoundException if the notification does not exist.
        """
        notification = await self._notification_repo.mark_read(
            session, notification_id, user_id,
        )
        if notification is None:
            raise NotFoundException(
                code=NOTIF_NOT_FOUND,
                message="Notification not found",
            )
        logger.debug("Marked notification %s as read for user %s", notification_id, user_id)
        return notification

    async def mark_all_read(self, session: AsyncSession, user_id: UUID) -> int:
        """Mark all unread notifications as read for a user. Returns count updated."""
        count = await self._notification_repo.mark_all_read(session, user_id)
        logger.debug("Marked %d notifications as read for user %s", count, user_id)
        return count

    async def create_notification(
        self,
        session: AsyncSession,
        data: NotificationCreate,
    ) -> Notification:
        """Create a new notification."""
        notification = Notification(
            organization_id=data.organization_id,
            user_id=data.user_id,
            type=data.type,
            title=data.title,
            message=data.message,
            data=data.data,
        )
        notification = await self._notification_repo.create(session, notification)
        logger.info(
            "Created notification %s (type=%s) for user %s in org %s",
            notification.id,
            notification.type,
            notification.user_id,
            notification.organization_id,
        )
        return notification

    async def delete_notification(
        self,
        session: AsyncSession,
        notification_id: UUID,
        user_id: UUID,
    ) -> bool:
        """Delete a notification.

        Raises NotFoundException if the notification does not exist.
        """
        deleted = await self._notification_repo.delete(session, notification_id, user_id)
        if not deleted:
            raise NotFoundException(
                code=NOTIF_NOT_FOUND,
                message="Notification not found",
            )
        logger.info("Deleted notification %s for user %s", notification_id, user_id)
        return True
