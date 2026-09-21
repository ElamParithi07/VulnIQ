from django.conf import settings
from django.db import models

from common.models import TimeStampedModel


class DailyDigest(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        READY = "ready", "Ready"
        SENT = "sent", "Sent"
        FAILED = "failed", "Failed"

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="daily_digests",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="daily_digests",
    )
    digest_date = models.DateField()
    generated_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    matching_vulnerability_count = models.PositiveIntegerField(default=0)
    backfill_vulnerability_count = models.PositiveIntegerField(default=0)
    rendered_subject = models.CharField(max_length=255, blank=True)
    rendered_html = models.TextField(blank=True)
    rendered_text = models.TextField(blank=True)

    class Meta:
        ordering = ["-digest_date", "-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "digest_date"],
                name="unique_daily_digest_per_org_date",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.organization} - {self.digest_date}"


class DailyDigestItem(TimeStampedModel):
    daily_digest = models.ForeignKey(
        DailyDigest,
        on_delete=models.CASCADE,
        related_name="items",
    )
    vulnerability = models.ForeignKey(
        "intel.Vulnerability",
        on_delete=models.CASCADE,
        related_name="digest_items",
    )
    rank = models.PositiveIntegerField()
    is_backfill = models.BooleanField(default=False)
    title = models.CharField(max_length=500, blank=True)
    vendor_name = models.CharField(max_length=255)
    product_name = models.CharField(max_length=255)
    cve_id = models.CharField(max_length=32)
    date_label = models.CharField(max_length=16, blank=True)
    severity_label = models.CharField(max_length=32, blank=True)
    cvss_base_score = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    epss_probability = models.DecimalField(max_digits=6, decimal_places=5, null=True, blank=True)
    is_kev = models.BooleanField(default=False)
    ai_summary = models.TextField(blank=True)
    ai_remediation = models.TextField(blank=True)

    class Meta:
        ordering = ["rank", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["daily_digest", "rank"],
                name="unique_digest_rank",
            ),
            models.UniqueConstraint(
                fields=["daily_digest", "vulnerability"],
                name="unique_vulnerability_per_digest",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.cve_id} ({self.product_name})"


class EmailSendAttempt(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        SENT = "sent", "Sent"
        FAILED = "failed", "Failed"

    daily_digest = models.ForeignKey(
        DailyDigest,
        on_delete=models.CASCADE,
        related_name="send_attempts",
    )
    attempt_number = models.PositiveIntegerField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    provider = models.CharField(max_length=64, default="resend")
    provider_message_id = models.CharField(max_length=255, blank=True)
    attempted_at = models.DateTimeField(auto_now_add=True)
    error_message = models.TextField(blank=True)

    class Meta:
        ordering = ["-attempted_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["daily_digest", "attempt_number"],
                name="unique_send_attempt_number_per_digest",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.daily_digest_id} - {self.status}"

# Create your models here.
