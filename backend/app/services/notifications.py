import logging
from urllib.parse import quote

from app.core.config import settings
from app.services.email import EmailDeliveryError, send_email

logger = logging.getLogger(__name__)


def _read_only_ticket_link(ticket_id: str) -> str:
    report_path = f"/report?ticket={quote(ticket_id, safe='')}"
    return_to = quote(report_path, safe="")
    return f"{settings.app_public_url.rstrip('/')}/login?returnTo={return_to}"


async def notify_ticket_created(
    reporter_email: str,
    ticket_id: str,
    summary: str,
    severity: str,
) -> None:
    link = _read_only_ticket_link(ticket_id)
    body = (
        f"Your bug report {ticket_id} has been received.\n\n"
        f"AI Summary: {summary}\n"
        f"Severity: {severity}\n\n"
        f"Read-only ticket ({ticket_id}): {link}\n"
    )
    try:
        await send_email(reporter_email, f"[{ticket_id}] Bug report received", body)
    except EmailDeliveryError:
        logger.exception("Ticket creation notification failed for %s to %s", ticket_id, reporter_email)


async def notify_ticket_status_changed(
    reporter_email: str,
    ticket_id: str,
    status: str,
    resolution_note: str | None,
) -> None:
    link = _read_only_ticket_link(ticket_id)
    note = resolution_note or "No additional note provided."
    body = (
        f"Your bug report {ticket_id} status changed to {status}.\n\n"
        f"Admin note:\n{note}\n\n"
        f"Read-only ticket ({ticket_id}): {link}\n"
    )
    try:
        await send_email(reporter_email, f"[{ticket_id}] Bug report status changed to {status}", body)
    except EmailDeliveryError:
        logger.exception("Ticket status notification failed for %s to %s", ticket_id, reporter_email)
