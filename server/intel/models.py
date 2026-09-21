from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from common.models import TimeStampedModel


class VulnerabilityStatus(models.TextChoices):
    PUBLISHED = "published", "Published"
    MODIFIED = "modified", "Modified"
    REJECTED = "rejected", "Rejected"
    UNKNOWN = "unknown", "Unknown"


class VulnerabilityProductStatus(models.TextChoices):
    MATCHED = "matched", "Matched"
    UNMATCHED = "unmatched", "Unmatched"
    AMBIGUOUS = "ambiguous", "Ambiguous"
    IGNORED = "ignored", "Ignored"


class AIEnrichmentStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    SUCCEEDED = "succeeded", "Succeeded"
    FAILED = "failed", "Failed"


class Vulnerability(TimeStampedModel):
    cve_id = models.CharField(max_length=32, unique=True)
    title = models.CharField(max_length=500, blank=True)
    description = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=VulnerabilityStatus.choices,
        default=VulnerabilityStatus.UNKNOWN,
    )
    cvss_score = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(10)],
    )
    epss_score = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(1)],
    )
    is_cisa_kev = models.BooleanField(default=False)
    priority_score = models.DecimalField(
        max_digits=6,
        decimal_places=3,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
    )
    published_at = models.DateTimeField(null=True, blank=True)
    last_modified_at = models.DateTimeField(null=True, blank=True)
    last_seen_in_feed_at = models.DateTimeField(null=True, blank=True)
    nvd_raw_json = models.JSONField(default=dict, blank=True)
    kev_raw_json = models.JSONField(default=dict, blank=True)
    epss_raw_json = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-priority_score", "cve_id"]
        indexes = [
            models.Index(fields=["status"], name="intel_vuln_status_idx"),
            models.Index(fields=["is_cisa_kev"], name="intel_vuln_kev_idx"),
            models.Index(fields=["priority_score"], name="intel_vuln_priority_idx"),
            models.Index(fields=["last_modified_at"], name="intel_vuln_modified_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(cvss_score__gte=0) & models.Q(cvss_score__lte=10)
                | models.Q(cvss_score__isnull=True),
                name="intel_vuln_cvss_range",
            ),
            models.CheckConstraint(
                condition=models.Q(epss_score__gte=0) & models.Q(epss_score__lte=1)
                | models.Q(epss_score__isnull=True),
                name="intel_vuln_epss_range",
            ),
            models.CheckConstraint(
                condition=models.Q(priority_score__gte=0)
                | models.Q(priority_score__isnull=True),
                name="intel_vuln_priority_nonnegative",
            ),
        ]

    def __str__(self) -> str:
        return self.cve_id


class VulnerabilityProduct(TimeStampedModel):
    vulnerability = models.ForeignKey(
        Vulnerability,
        on_delete=models.CASCADE,
        related_name="products",
    )
    raw_vendor = models.CharField(max_length=255)
    raw_product = models.CharField(max_length=255)
    normalized_vendor = models.CharField(max_length=255)
    normalized_product = models.CharField(max_length=255)
    tech_tag = models.ForeignKey(
        "taxonomy.TechTag",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="matched_vulnerability_products",
    )
    source_cpe = models.TextField(blank=True)
    match_status = models.CharField(
        max_length=20,
        choices=VulnerabilityProductStatus.choices,
        default=VulnerabilityProductStatus.UNMATCHED,
    )

    class Meta:
        ordering = ["normalized_vendor", "normalized_product", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["vulnerability", "normalized_vendor", "normalized_product"],
                name="intel_vuln_product_unique_normalized",
            ),
        ]
        indexes = [
            models.Index(
                fields=["normalized_product"],
                name="intel_vuln_prod_norm_prod_idx",
            ),
            models.Index(
                fields=["normalized_vendor", "normalized_product"],
                name="intel_vuln_prod_norm_look_idx",
            ),
            models.Index(fields=["match_status"], name="intel_vuln_prod_status_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.vulnerability.cve_id}: {self.normalized_vendor}/{self.normalized_product}"


class VulnerabilityAIEnrichment(TimeStampedModel):
    vulnerability = models.OneToOneField(
        Vulnerability,
        on_delete=models.CASCADE,
        related_name="latest_enrichment",
    )
    provider = models.CharField(max_length=100)
    model_name = models.CharField(max_length=150)
    prompt_version = models.CharField(max_length=50)
    input_hash = models.CharField(max_length=128)
    summary_text = models.TextField(blank=True)
    remediation_text = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=AIEnrichmentStatus.choices,
        default=AIEnrichmentStatus.PENDING,
    )
    error_message = models.TextField(blank=True)
    generated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-generated_at", "-created_at"]
        indexes = [
            models.Index(fields=["status"], name="intel_ai_status_idx"),
            models.Index(fields=["generated_at"], name="intel_ai_generated_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.vulnerability.cve_id} [{self.provider}]"
