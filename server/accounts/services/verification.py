import secrets

from django.core.mail import send_mail
from django.db import transaction
from django.urls import reverse
from django.utils import timezone

from accounts.models import EmailVerificationToken, User


def issue_email_verification_token(user: User) -> EmailVerificationToken:
    with transaction.atomic():
        user.verification_tokens.filter(consumed_at__isnull=True).update(consumed_at=timezone.now())
        token = EmailVerificationToken.objects.create(
            user=user,
            token=secrets.token_urlsafe(32),
            expires_at=EmailVerificationToken.build_expiry(),
        )
    return token


def send_verification_email(user: User) -> EmailVerificationToken:
    token = issue_email_verification_token(user)
    verification_path = reverse("accounts:verify-email", kwargs={"token": token.token})

    send_mail(
        subject="Verify your VulnIQ email",
        message=f"Verify your account by visiting: {verification_path}",
        from_email=None,
        recipient_list=[user.email],
    )
    return token


def verify_email_token(token_value: str) -> User | None:
    token = (
        EmailVerificationToken.objects.select_related("user")
        .filter(token=token_value)
        .order_by("-created_at")
        .first()
    )
    if token is None or not token.is_active:
        return None

    with transaction.atomic():
        token.consumed_at = timezone.now()
        token.save(update_fields=["consumed_at", "updated_at"])
        token.user.is_email_verified = True
        token.user.save(update_fields=["is_email_verified", "updated_at"])
    return token.user
