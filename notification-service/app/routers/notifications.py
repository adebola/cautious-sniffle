"""Public-facing notification endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends

from chatcraft_common.auth import CurrentUser, get_current_user
from chatcraft_common.pagination import PaginationParams

from app.dependencies import get_notification_service, get_session
from app.schemas.notification import NotificationResponse, UnreadCountResponse
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/api/v1/notifications", tags=["notifications"])


@router.get("/", response_model=dict)
async def list_notifications(
    pagination: PaginationParams = Depends(),
    user: CurrentUser = Depends(get_current_user),
    session=Depends(get_session),
    service: NotificationService = Depends(get_notification_service),
):
    """List notifications for the authenticated user (paginated, newest first)."""
    result = await service.list_notifications(
        session=session,
        user_id=user.user_id,
        page=pagination.page,
        page_size=pagination.page_size,
    )
    return result.model_dump(mode="json")


@router.get("/unread-count", response_model=dict)
async def get_unread_count(
    user: CurrentUser = Depends(get_current_user),
    session=Depends(get_session),
    service: NotificationService = Depends(get_notification_service),
):
    """Get the number of unread notifications for the authenticated user."""
    count = await service.get_unread_count(session, user.user_id)
    data = UnreadCountResponse(count=count).model_dump(mode="json")
    return {"data": data}


@router.post("/{notification_id}/read", response_model=dict)
async def mark_notification_read(
    notification_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    session=Depends(get_session),
    service: NotificationService = Depends(get_notification_service),
):
    """Mark a single notification as read."""
    notification = await service.mark_read(session, notification_id, user.user_id)
    data = NotificationResponse.model_validate(notification).model_dump(mode="json")
    return {"data": data}


@router.post("/read-all", response_model=dict)
async def mark_all_read(
    user: CurrentUser = Depends(get_current_user),
    session=Depends(get_session),
    service: NotificationService = Depends(get_notification_service),
):
    """Mark all unread notifications as read for the authenticated user."""
    count = await service.mark_all_read(session, user.user_id)
    return {"data": {"updated": count}}


@router.delete("/{notification_id}", response_model=dict)
async def delete_notification(
    notification_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    session=Depends(get_session),
    service: NotificationService = Depends(get_notification_service),
):
    """Delete a notification."""
    await service.delete_notification(session, notification_id, user.user_id)
    return {"data": {"deleted": True}}
