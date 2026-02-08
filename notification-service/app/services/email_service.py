"""Email delivery via Brevo (formerly Sendinblue) REST API."""

import logging
from pathlib import Path

import httpx
from jinja2 import Environment, FileSystemLoader, TemplateNotFound

from app.config import Settings

logger = logging.getLogger(__name__)

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"


class EmailService:
    """Service for rendering Jinja2 email templates and sending via Brevo."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._jinja_env = Environment(
            loader=FileSystemLoader(str(TEMPLATES_DIR)),
            autoescape=True,
        )

    async def send_email(
        self,
        to_email: str,
        to_name: str,
        subject: str,
        template_name: str,
        template_data: dict,
    ) -> bool:
        """Render an HTML email template and send it via Brevo.

        This is a fire-and-forget operation: errors are logged but not raised,
        so callers are never blocked by email delivery failures.

        Returns True if the email was sent successfully, False otherwise.
        """
        # Render the template
        try:
            template = self._jinja_env.get_template(template_name)
            html_content = template.render(**template_data)
        except TemplateNotFound:
            logger.error("Email template not found: %s", template_name)
            return False
        except Exception:
            logger.exception("Failed to render email template: %s", template_name)
            return False

        # Check for API key
        if not self._settings.brevo_api_key:
            logger.warning(
                "Brevo API key not configured; skipping email to %s (subject: %s)",
                to_email,
                subject,
            )
            return False

        # Send via Brevo REST API
        url = f"{self._settings.brevo_api_url}/smtp/email"
        headers = {
            "api-key": self._settings.brevo_api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        payload = {
            "sender": {
                "email": self._settings.brevo_sender_email,
                "name": self._settings.brevo_sender_name,
            },
            "to": [
                {
                    "email": to_email,
                    "name": to_name,
                }
            ],
            "subject": subject,
            "htmlContent": html_content,
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
            logger.info(
                "Email sent successfully to %s (subject: %s)",
                to_email,
                subject,
            )
            return True
        except httpx.HTTPStatusError as exc:
            logger.error(
                "Brevo API returned %d for email to %s: %s",
                exc.response.status_code,
                to_email,
                exc.response.text,
            )
            return False
        except Exception:
            logger.exception("Failed to send email to %s via Brevo", to_email)
            return False
