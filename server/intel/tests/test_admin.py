import pytest
from django.urls import reverse

from accounts.models import User
from intel.clients.gemini import GeminiClientError
from intel.models import Vulnerability, VulnerabilityAIEnrichment, VulnerabilityProduct, VulnerabilityProductStatus
from taxonomy.models import TechTag, TechTagAlias, TechTagCategory


def _make_admin_client(client):
    admin_user = User.objects.create_user(
        email="admin@vulniq.local", password="secret123", is_staff=True, is_superuser=True
    )
    client.force_login(admin_user)
    return client


def _make_unmatched_product(cve_id="CVE-2026-0001", normalized_product="win srv"):
    vulnerability = Vulnerability.objects.create(cve_id=cve_id)
    return VulnerabilityProduct.objects.create(
        vulnerability=vulnerability,
        raw_vendor="microsoft",
        raw_product="win srv",
        normalized_vendor="microsoft",
        normalized_product=normalized_product,
        match_status=VulnerabilityProductStatus.UNMATCHED,
    )


@pytest.mark.django_db
def test_mark_as_ignored_action(client):
    _make_admin_client(client)
    product = _make_unmatched_product()

    client.post(
        reverse("admin:intel_vulnerabilityproduct_changelist"),
        {"action": "mark_as_ignored", "_selected_action": [str(product.pk)]},
    )
    product.refresh_from_db()

    assert product.match_status == VulnerabilityProductStatus.IGNORED


@pytest.mark.django_db
def test_resolve_unmatched_products_shows_intermediate_page(client):
    _make_admin_client(client)
    product = _make_unmatched_product()

    response = client.post(
        reverse("admin:intel_vulnerabilityproduct_changelist"),
        {"action": "resolve_unmatched_products", "_selected_action": [str(product.pk)]},
    )

    assert response.status_code == 200
    assert b"Resolve unmatched products" in response.content


@pytest.mark.django_db
def test_resolve_unmatched_products_links_to_existing_tag_and_creates_alias(client):
    _make_admin_client(client)
    tag = TechTag.objects.create(name="Windows Server", category=TechTagCategory.PRODUCT)
    product = _make_unmatched_product(normalized_product="win srv")

    client.post(
        reverse("admin:intel_vulnerabilityproduct_changelist"),
        {
            "action": "resolve_unmatched_products",
            "_selected_action": [str(product.pk)],
            "apply": "Apply",
            "resolution": "existing",
            "existing_tag": str(tag.pk),
        },
    )
    product.refresh_from_db()

    assert product.match_status == VulnerabilityProductStatus.MATCHED
    assert product.tech_tag == tag
    assert TechTagAlias.objects.filter(tag=tag, normalized_alias="win srv").exists()


@pytest.mark.django_db
def test_resolve_unmatched_products_creates_new_canonical_tag(client):
    _make_admin_client(client)
    product = _make_unmatched_product(normalized_product="brand new thing")

    client.post(
        reverse("admin:intel_vulnerabilityproduct_changelist"),
        {
            "action": "resolve_unmatched_products",
            "_selected_action": [str(product.pk)],
            "apply": "Apply",
            "resolution": "new",
            "new_tag_name": "Brand New Thing",
        },
    )
    product.refresh_from_db()

    tag = TechTag.objects.get(name="Brand New Thing")
    assert product.match_status == VulnerabilityProductStatus.MATCHED
    assert product.tech_tag == tag


@pytest.mark.django_db
def test_regenerate_ai_enrichment_action(client, monkeypatch):
    _make_admin_client(client)
    vulnerability = Vulnerability.objects.create(cve_id="CVE-2026-0001")
    VulnerabilityAIEnrichment.objects.create(
        vulnerability=vulnerability,
        provider="gemini",
        model_name="gemini-2.5-flash",
        prompt_version="v1",
        input_hash="stale-hash",
        summary_text="old summary",
        remediation_text="old remediation",
    )

    class StubClient:
        model_name = "gemini-2.5-flash"

        def generate_text(self, prompt):
            return "SUMMARY: fresh summary.\nREMEDIATION: fresh remediation."

    monkeypatch.setattr(
        "intel.services.enrichment.GeminiClient", lambda **kwargs: StubClient()
    )

    client.post(
        reverse("admin:intel_vulnerability_changelist"),
        {"action": "regenerate_ai_enrichment", "_selected_action": [str(vulnerability.pk)]},
    )

    enrichment = VulnerabilityAIEnrichment.objects.get(vulnerability=vulnerability)
    assert enrichment.summary_text == "fresh summary."
