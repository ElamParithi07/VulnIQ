from __future__ import annotations

import hashlib

from django.conf import settings
from django.utils import timezone

from intel.clients.gemini import GeminiClient, GeminiClientError
from intel.models import AIEnrichmentStatus, Vulnerability, VulnerabilityAIEnrichment
from intel.services.ai_prompts import (
    PROMPT_VERSION,
    PromptParsingError,
    build_enrichment_prompt,
    parse_enrichment_response,
)

PROVIDER_NAME = "gemini"

FALLBACK_SUMMARY = (
    "An AI-generated summary is temporarily unavailable for this vulnerability. "
    "Use the CVSS/EPSS scores and CISA KEV status above to assess urgency."
)
FALLBACK_REMEDIATION = (
    "Apply vendor-provided patches or updates for the affected product as soon as possible, "
    "and follow your organization's standard vulnerability remediation process."
)


def _latest_enrichment(vulnerability: Vulnerability) -> VulnerabilityAIEnrichment | None:
    try:
        return vulnerability.latest_enrichment
    except VulnerabilityAIEnrichment.DoesNotExist:
        return None


def _compute_input_hash(vulnerability: Vulnerability, vendor: str, product: str) -> str:
    raw = "|".join(
        [
            vulnerability.cve_id,
            vulnerability.title or "",
            vulnerability.description or "",
            str(vulnerability.cvss_score) if vulnerability.cvss_score is not None else "",
            str(vulnerability.epss_score) if vulnerability.epss_score is not None else "",
            "1" if vulnerability.is_cisa_kev else "0",
            vendor or "",
            product or "",
            PROMPT_VERSION,
        ]
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def generate_enrichment(
    vulnerability: Vulnerability,
    *,
    vendor: str = "",
    product: str = "",
    client: GeminiClient | None = None,
) -> VulnerabilityAIEnrichment:
    """Generate (or reuse) the latest AI enrichment for a vulnerability.

    Reuses the existing enrichment untouched when it already succeeded for
    the same input (same scoring/product context and prompt version) so a
    digest rerun never re-spends an API call. On provider failure or an
    unparsable response, persists deterministic fallback text with a FAILED
    status rather than leaving the digest item without guidance.
    """
    input_hash = _compute_input_hash(vulnerability, vendor, product)

    existing = _latest_enrichment(vulnerability)
    if (
        existing is not None
        and existing.status == AIEnrichmentStatus.SUCCEEDED
        and existing.input_hash == input_hash
    ):
        return existing

    active_client = client or GeminiClient(
        api_key=settings.GEMINI_API_KEY,
        model_name=settings.GEMINI_MODEL_NAME,
    )

    prompt = build_enrichment_prompt(
        title=vulnerability.title,
        description=vulnerability.description,
        cvss_score=vulnerability.cvss_score,
        epss_score=vulnerability.epss_score,
        is_kev=vulnerability.is_cisa_kev,
        vendor=vendor,
        product=product,
    )

    try:
        raw_text = active_client.generate_text(prompt)
        summary_text, remediation_text = parse_enrichment_response(raw_text)
        status = AIEnrichmentStatus.SUCCEEDED
        error_message = ""
    except (GeminiClientError, PromptParsingError) as exc:
        summary_text, remediation_text = FALLBACK_SUMMARY, FALLBACK_REMEDIATION
        status = AIEnrichmentStatus.FAILED
        error_message = str(exc)

    enrichment, _created = VulnerabilityAIEnrichment.objects.update_or_create(
        vulnerability=vulnerability,
        defaults={
            "provider": PROVIDER_NAME,
            "model_name": active_client.model_name,
            "prompt_version": PROMPT_VERSION,
            "input_hash": input_hash,
            "summary_text": summary_text,
            "remediation_text": remediation_text,
            "status": status,
            "error_message": error_message,
            "generated_at": timezone.now(),
        },
    )
    return enrichment
