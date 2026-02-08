"""Internal endpoints consumed by other microservices (not routed via Gateway)."""

import logging

from fastapi import APIRouter, Depends

from app.dependencies import get_email_service, get_notification_service, get_session
from app.schemas.notification import NotificationCreate, NotificationResponse, SendEmailRequest
from app.services.email_service import EmailService
from app.services.notification_service import NotificationService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/internal/notifications", tags=["internal"])


@router.post("/", response_model=dict)
async def create_notification(
    body: NotificationCreate,
    session=Depends(get_session),
    service: NotificationService = Depends(get_notification_service),
):
    """Create a new in-app notification.

    Called by other services to notify users about events such as
    invitations, workspace additions, document processing results, or billing updates.
    """
    notification = await service.create_notification(session, body)
    data = NotificationResponse.model_validate(notification).model_dump(mode="json")
    return {"data": data}


@router.post("/email", response_model=dict)
async def send_email(
    body: SendEmailRequest,
    email_service: EmailService = Depends(get_email_service),
):
    """Send an email using a Jinja2 template via Brevo.

    Called by other services to send transactional emails such as
    invitations, password resets, and processing notifications.
    This is fire-and-forget; failures are logged but do not cause errors.
    """
    success = await email_service.send_email(
        to_email=body.to_email,
        to_name=body.to_name,
        subject=body.subject,
        template_name=body.template_name,
        template_data=body.template_data,
    )
    return {"data": {"sent": success}}
