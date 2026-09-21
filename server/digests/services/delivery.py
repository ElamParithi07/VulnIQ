from __future__ import annotations

from django.conf import settings
from django.db import transaction
from django.template.loader import render_to_string
from django.utils import timezone

from digests.clients.resend import ResendClient, ResendClientError
from digests.models import DailyDigest, EmailSendAttempt
from digests.services.email_context import build_email_context, build_email_subject


def _ensure_rendered_content(digest: DailyDigest) -> DailyDigest:
    """Render subject/html/text once and persist on the digest snapshot.

    Every later call (including retries) reuses these stored fields instead
    of rebuilding them from live data, per the retry-reuses-same-snapshot
    rule.
    """
    if digest.rendered_subject and digest.rendered_html and digest.rendered_text:
        return digest

    context = build_email_context(digest)
    digest.rendered_subject = build_email_subject(digest)
    digest.rendered_html = render_to_string("digests/email_digest.html", context)
    digest.rendered_text = render_to_string("digests/email_digest.txt", context)
    digest.save(update_fields=["rendered_subject", "rendered_html", "rendered_text", "updated_at"])
    return digest


def send_digest(digest: DailyDigest, *, client: ResendClient | None = None) -> EmailSendAttempt:
    """Send (or resend) one digest snapshot's already-rendered content.

    Each call is recorded as a numbered EmailSendAttempt. Resend accepting
    the request is treated as delivered for MVP (no webhook confirmation).
    """
    digest = _ensure_rendered_content(digest)
    active_client = client or ResendClient(api_key=settings.RESEND_API_KEY)
    next_attempt_number = digest.send_attempts.count() + 1

    try:
        message_id = active_client.send_email(
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=digest.user.email,
            subject=digest.rendered_subject,
            html=digest.rendered_html,
            text=digest.rendered_text,
        )
    except ResendClientError as exc:
        with transaction.atomic():
            attempt = EmailSendAttempt.objects.create(
                daily_digest=digest,
                attempt_number=next_attempt_number,
                status=EmailSendAttempt.Status.FAILED,
                error_message=str(exc),
            )
            digest.status = DailyDigest.Status.FAILED
            digest.save(update_fields=["status", "updated_at"])
        return attempt

    with transaction.atomic():
        attempt = EmailSendAttempt.objects.create(
            daily_digest=digest,
            attempt_number=next_attempt_number,
            status=EmailSendAttempt.Status.SENT,
            provider_message_id=message_id,
        )
        digest.status = DailyDigest.Status.SENT
        if digest.sent_at is None:
            digest.sent_at = timezone.now()
        digest.save(update_fields=["status", "sent_at", "updated_at"])

    return attempt
