import datetime as dt
from decimal import Decimal

import pytest
from django.template.loader import render_to_string

from accounts.models import Organization, User
from digests.services.email_context import build_email_context, build_email_subject
from digests.services.snapshots import build_daily_digest
from intel.models import Vulnerability, VulnerabilityAIEnrichment, VulnerabilityProduct, VulnerabilityProductStatus, VulnerabilityStatus
from taxonomy.models import TechTag, TechTagCategory, UserTechTag

WINDOW_START = dt.datetime(2026, 8, 8, 0, 0, tzinfo=dt.UTC)
WINDOW_END = dt.datetime(2026, 8, 9, 0, 0, tzinfo=dt.UTC)
IN_WINDOW = dt.datetime(2026, 8, 8, 12, 0, tzinfo=dt.UTC)
DIGEST_DATE = dt.date(2026, 8, 9)


def _make_org(slug="acme", name="Acme"):
    org = Organization.objects.create(name=name, slug=slug)
    User.objects.create_user(email=f"owner@{slug}.test", password="secret123", organization=org)
    return org


def _make_matched_vulnerability(org, cve_id="CVE-2026-0001"):
    tag, _ = TechTag.objects.get_or_create(name="Windows Server", defaults={"category": TechTagCategory.PRODUCT})
    UserTechTag.objects.get_or_create(user=org.user, tag=tag)
    vulnerability = Vulnerability.objects.create(
        cve_id=cve_id,
        title="Remote code execution in Windows Server",
        status=VulnerabilityStatus.PUBLISHED,
        priority_score=Decimal("9.71"),
        cvss_score=Decimal("9.8"),
        epss_score=Decimal("0.93"),
        is_cisa_kev=True,
        published_at=IN_WINDOW,
        last_modified_at=IN_WINDOW,
    )
    VulnerabilityProduct.objects.create(
        vulnerability=vulnerability,
        raw_vendor="microsoft",
        raw_product="windows server",
        normalized_vendor="microsoft",
        normalized_product="windows server",
        tech_tag=tag,
        match_status=VulnerabilityProductStatus.MATCHED,
    )
    VulnerabilityAIEnrichment.objects.create(
        vulnerability=vulnerability,
        provider="gemini",
        model_name="gemini-2.5-flash",
        prompt_version="v1",
        input_hash="abc123",
        summary_text="Attackers can run code remotely with no user interaction.",
        remediation_text="Apply the vendor patch immediately.",
    )
    return vulnerability


def _make_backfill_only_digest(org):
    Vulnerability.objects.create(
        cve_id="CVE-2026-8888",
        title="Global backfill threat",
        status=VulnerabilityStatus.PUBLISHED,
        priority_score=Decimal("7.0"),
        last_modified_at=IN_WINDOW,
    )
    return build_daily_digest(org, digest_date=DIGEST_DATE, window_start=WINDOW_START, window_end=WINDOW_END)


@pytest.mark.django_db
def test_build_email_context_includes_chips_and_scores():
    org = _make_org()
    _make_matched_vulnerability(org)
    digest = build_daily_digest(org, digest_date=DIGEST_DATE, window_start=WINDOW_START, window_end=WINDOW_END)

    context = build_email_context(digest)

    assert context["organization_name"] == "Acme"
    assert context["is_fully_backfill"] is False
    item = context["items"][0]
    assert item["cve_id"] == "CVE-2026-0001"
    assert set(item["chips"]) == {"Actively Exploited", "High EPSS", "Critical"}
    assert item["ai_summary"] == "Attackers can run code remotely with no user interaction."
    assert item["date_label"] == "Published"


@pytest.mark.django_db
def test_build_email_context_flags_fully_backfill_digest():
    org = _make_org()
    digest = _make_backfill_only_digest(org)

    context = build_email_context(digest)

    assert context["is_fully_backfill"] is True
    assert context["items"][0]["cve_id"] == "CVE-2026-8888"


@pytest.mark.django_db
def test_build_email_subject_normal_vs_no_match():
    org = _make_org()
    _make_matched_vulnerability(org)
    normal_digest = build_daily_digest(org, digest_date=DIGEST_DATE, window_start=WINDOW_START, window_end=WINDOW_END)
    assert "Top Global Threats" not in build_email_subject(normal_digest)

    org2 = _make_org(slug="acme-2", name="Acme 2")
    backfill_digest = _make_backfill_only_digest(org2)
    assert "Top Global Threats" in build_email_subject(backfill_digest)


@pytest.mark.django_db
def test_html_template_renders_required_item_fields():
    org = _make_org()
    _make_matched_vulnerability(org)
    digest = build_daily_digest(org, digest_date=DIGEST_DATE, window_start=WINDOW_START, window_end=WINDOW_END)

    html = render_to_string("digests/email_digest.html", build_email_context(digest))

    assert "CVE-2026-0001" in html
    assert "Remote code execution in Windows Server" in html
    assert "Actively Exploited" in html
    assert "Attackers can run code remotely" in html
    assert "Apply the vendor patch immediately." in html
    assert "/dashboard/" in html
    assert "Manage digest settings" in html


@pytest.mark.django_db
def test_text_template_renders_required_item_fields_without_html_tags():
    org = _make_org()
    _make_matched_vulnerability(org)
    digest = build_daily_digest(org, digest_date=DIGEST_DATE, window_start=WINDOW_START, window_end=WINDOW_END)

    text = render_to_string("digests/email_digest.txt", build_email_context(digest))

    assert "CVE-2026-0001" in text
    assert "Summary: Attackers can run code remotely" in text
    assert "Remediation: Apply the vendor patch immediately." in text
    assert "<div" not in text
    assert "<html" not in text


@pytest.mark.django_db
def test_no_match_note_rendered_in_both_templates():
    org = _make_org()
    digest = _make_backfill_only_digest(org)
    context = build_email_context(digest)

    html = render_to_string("digests/email_digest.html", context)
    text = render_to_string("digests/email_digest.txt", context)

    assert "top global threats instead" in html
    assert "top global threats instead" in text


@pytest.mark.django_db
def test_short_digest_does_not_pad_with_synthetic_items():
    org = _make_org()
    _make_matched_vulnerability(org)
    digest = build_daily_digest(org, digest_date=DIGEST_DATE, window_start=WINDOW_START, window_end=WINDOW_END)

    context = build_email_context(digest)

    assert len(context["items"]) == 1
