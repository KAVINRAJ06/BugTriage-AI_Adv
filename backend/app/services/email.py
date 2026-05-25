import logging

import aiosmtplib
from email.message import EmailMessage

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmailDeliveryError(RuntimeError):
    pass


async def send_email(to_email: str, subject: str, body: str) -> None:
    if not settings.smtp_configured:
        raise EmailDeliveryError("SMTP is not configured")

    message = EmailMessage()
    message["From"] = settings.smtp_from
    message["To"] = to_email
    message["Subject"] = subject
    message.set_content(body)

    try:
        await aiosmtplib.send(
            message,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_user or None,
            password=settings.smtp_password or None,
            start_tls=settings.smtp_start_tls,
            use_tls=settings.smtp_tls,
        )
    except aiosmtplib.SMTPException as exc:
        logger.exception("Email delivery failed for to=%s subject=%s", to_email, subject)
        raise EmailDeliveryError("Email delivery failed") from exc


async def send_otp_email(to_email: str, otp: str) -> None:
    body = (
        f"Your one-time verification code is: {otp}\n\n"
        f"This code expires in {settings.otp_expire_minutes} minutes.\n"
        "If you did not request this, ignore this email."
    )
    await send_email(to_email, "Your verification code", body)
