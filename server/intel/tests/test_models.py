import pytest
from django.db import IntegrityError, transaction

from intel.models import (
    AIEnrichmentStatus,
    Vulnerability,
    VulnerabilityAIEnrichment,
    VulnerabilityProduct,
    VulnerabilityProductStatus,
    VulnerabilityStatus,
)


def _create_vulnerability(cve_id: str = "CVE-2026-0001", **kwargs):
    return Vulnerability.objects.create(cve_id=cve_id, **kwargs)


@pytest.mark.django_db
def test_cve_id_is_unique():
    _create_vulnerability()

    with pytest.raises(IntegrityError):
        Vulnerability.objects.create(cve_id="CVE-2026-0001")


@pytest.mark.django_db
def test_vulnerability_defaults():
    vulnerability = _create_vulnerability()

    assert vulnerability.status == VulnerabilityStatus.UNKNOWN
    assert vulnerability.is_cisa_kev is False
    assert vulnerability.cvss_score is None
    assert vulnerability.priority_score is None


@pytest.mark.django_db
def test_cvss_score_out_of_range_is_rejected():
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            _create_vulnerability(cvss_score="10.5")


@pytest.mark.django_db
def test_epss_score_out_of_range_is_rejected():
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            _create_vulnerability(epss_score="1.5")


@pytest.mark.django_db
def test_priority_score_negative_is_rejected():
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            _create_vulnerability(priority_score="-1")


@pytest.mark.django_db
def test_vulnerability_product_unique_normalized_pair_per_vulnerability():
    vulnerability = _create_vulnerability()
    VulnerabilityProduct.objects.create(
        vulnerability=vulnerability,
        raw_vendor="Microsoft",
        raw_product="Windows Server",
        normalized_vendor="microsoft",
        normalized_product="windows_server",
    )

    with pytest.raises(IntegrityError):
        VulnerabilityProduct.objects.create(
            vulnerability=vulnerability,
            raw_vendor="microsoft ",
            raw_product="windows server",
            normalized_vendor="microsoft",
            normalized_product="windows_server",
        )


@pytest.mark.django_db
def test_vulnerability_product_default_status_is_unmatched():
    vulnerability = _create_vulnerability()
    product = VulnerabilityProduct.objects.create(
        vulnerability=vulnerability,
        raw_vendor="Apache",
        raw_product="HTTP Server",
        normalized_vendor="apache",
        normalized_product="http_server",
    )

    assert product.match_status == VulnerabilityProductStatus.UNMATCHED


@pytest.mark.django_db
def test_vulnerability_product_same_normalized_pair_allowed_across_vulnerabilities():
    first = _create_vulnerability(cve_id="CVE-2026-0001")
    second = _create_vulnerability(cve_id="CVE-2026-0002")

    for vulnerability in (first, second):
        VulnerabilityProduct.objects.create(
            vulnerability=vulnerability,
            raw_vendor="Apache",
            raw_product="HTTP Server",
            normalized_vendor="apache",
            normalized_product="http_server",
        )

    assert VulnerabilityProduct.objects.filter(
        normalized_vendor="apache", normalized_product="http_server"
    ).count() == 2


@pytest.mark.django_db
def test_vulnerability_has_at_most_one_latest_enrichment():
    vulnerability = _create_vulnerability()
    VulnerabilityAIEnrichment.objects.create(
        vulnerability=vulnerability,
        provider="gemini",
        model_name="gemini-2.5-flash",
        prompt_version="v1",
        input_hash="abc123",
        status=AIEnrichmentStatus.SUCCEEDED,
    )

    with pytest.raises(IntegrityError):
        VulnerabilityAIEnrichment.objects.create(
            vulnerability=vulnerability,
            provider="gemini",
            model_name="gemini-2.5-flash",
            prompt_version="v2",
            input_hash="def456",
            status=AIEnrichmentStatus.SUCCEEDED,
        )


@pytest.mark.django_db
def test_enrichment_defaults_to_pending():
    vulnerability = _create_vulnerability()
    enrichment = VulnerabilityAIEnrichment.objects.create(
        vulnerability=vulnerability,
        provider="gemini",
        model_name="gemini-2.5-flash",
        prompt_version="v1",
        input_hash="abc123",
    )

    assert enrichment.status == AIEnrichmentStatus.PENDING
    assert vulnerability.latest_enrichment == enrichment
