from decimal import Decimal

import pytest

from intel.clients.gemini import GeminiClientError
from intel.models import AIEnrichmentStatus, Vulnerability, VulnerabilityAIEnrichment
from intel.services.enrichment import FALLBACK_REMEDIATION, FALLBACK_SUMMARY, generate_enrichment


class StubGeminiClient:
    model_name = "gemini-2.5-flash"

    def __init__(self, text=None, error=None):
        self.text = text
        self.error = error
        self.call_count = 0

    def generate_text(self, prompt):
        self.call_count += 1
        if self.error:
            raise self.error
        return self.text


def _make_vulnerability(**kwargs):
    defaults = {
        "cve_id": "CVE-2026-0001",
        "title": "RCE in Windows Server",
        "description": "Remote code execution issue",
        "cvss_score": Decimal("9.8"),
        "epss_score": Decimal("0.93"),
        "is_cisa_kev": True,
    }
    defaults.update(kwargs)
    return Vulnerability.objects.create(**defaults)


@pytest.mark.django_db
def test_generate_enrichment_success_persists_summary_and_remediation():
    vulnerability = _make_vulnerability()
    client = StubGeminiClient(text="SUMMARY: Attackers can run code.\nREMEDIATION: Patch now.")

    enrichment = generate_enrichment(vulnerability, vendor="microsoft", product="windows server", client=client)

    assert enrichment.status == AIEnrichmentStatus.SUCCEEDED
    assert enrichment.summary_text == "Attackers can run code."
    assert enrichment.remediation_text == "Patch now."
    assert enrichment.provider == "gemini"
    assert enrichment.prompt_version == "v1"
    assert client.call_count == 1


@pytest.mark.django_db
def test_generate_enrichment_falls_back_on_client_error():
    vulnerability = _make_vulnerability()
    client = StubGeminiClient(error=GeminiClientError("provider down"))

    enrichment = generate_enrichment(vulnerability, client=client)

    assert enrichment.status == AIEnrichmentStatus.FAILED
    assert enrichment.summary_text == FALLBACK_SUMMARY
    assert enrichment.remediation_text == FALLBACK_REMEDIATION
    assert "provider down" in enrichment.error_message


@pytest.mark.django_db
def test_generate_enrichment_falls_back_on_malformed_response():
    vulnerability = _make_vulnerability()
    client = StubGeminiClient(text="not the expected format")

    enrichment = generate_enrichment(vulnerability, client=client)

    assert enrichment.status == AIEnrichmentStatus.FAILED
    assert enrichment.summary_text == FALLBACK_SUMMARY
    assert enrichment.remediation_text == FALLBACK_REMEDIATION


@pytest.mark.django_db
def test_generate_enrichment_reuses_existing_succeeded_enrichment_without_recalling_client():
    vulnerability = _make_vulnerability()
    client = StubGeminiClient(text="SUMMARY: first.\nREMEDIATION: first fix.")

    first = generate_enrichment(vulnerability, vendor="microsoft", product="windows server", client=client)
    second = generate_enrichment(vulnerability, vendor="microsoft", product="windows server", client=client)

    assert first.id == second.id
    assert client.call_count == 1
    assert VulnerabilityAIEnrichment.objects.filter(vulnerability=vulnerability).count() == 1


@pytest.mark.django_db
def test_generate_enrichment_regenerates_when_underlying_data_changes():
    vulnerability = _make_vulnerability()
    client = StubGeminiClient(text="SUMMARY: first.\nREMEDIATION: first fix.")
    generate_enrichment(vulnerability, vendor="microsoft", product="windows server", client=client)

    vulnerability.cvss_score = Decimal("5.0")
    vulnerability.save(update_fields=["cvss_score"])

    client.text = "SUMMARY: second.\nREMEDIATION: second fix."
    second = generate_enrichment(vulnerability, vendor="microsoft", product="windows server", client=client)

    assert client.call_count == 2
    assert second.summary_text == "second."
    assert VulnerabilityAIEnrichment.objects.filter(vulnerability=vulnerability).count() == 1


@pytest.mark.django_db
def test_generate_enrichment_retries_after_previous_failure():
    vulnerability = _make_vulnerability()
    failing_client = StubGeminiClient(error=GeminiClientError("down"))
    generate_enrichment(vulnerability, vendor="microsoft", product="windows server", client=failing_client)

    working_client = StubGeminiClient(text="SUMMARY: recovered.\nREMEDIATION: fixed now.")
    enrichment = generate_enrichment(
        vulnerability, vendor="microsoft", product="windows server", client=working_client
    )

    assert enrichment.status == AIEnrichmentStatus.SUCCEEDED
    assert enrichment.summary_text == "recovered."
    assert VulnerabilityAIEnrichment.objects.filter(vulnerability=vulnerability).count() == 1
