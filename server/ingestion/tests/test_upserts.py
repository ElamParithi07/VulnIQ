import datetime as dt

import pytest

from intel.models import Vulnerability, VulnerabilityProduct, VulnerabilityProductStatus, VulnerabilityStatus
from ingestion.services.upserts import upsert_epss_score, upsert_kev_status, upsert_nvd_vulnerability
from taxonomy.models import TechTag, TechTagCategory


def _nvd_parsed(**overrides):
    parsed = {
        "cve_id": "CVE-2026-0001",
        "title": "Remote code execution issue",
        "description": "Remote code execution issue",
        "status": VulnerabilityStatus.PUBLISHED,
        "cvss_score": 9.8,
        "published_at": dt.datetime(2026, 8, 1, tzinfo=dt.UTC),
        "last_modified_at": dt.datetime(2026, 8, 8, tzinfo=dt.UTC),
        "cpe_list": ["cpe:2.3:a:microsoft:windows_server:2019:*:*:*:*:*:*:*"],
        "raw_json": {"cve": {"id": "CVE-2026-0001"}},
    }
    parsed.update(overrides)
    return parsed


@pytest.mark.django_db
def test_upsert_nvd_vulnerability_creates_record_and_products():
    vulnerability = upsert_nvd_vulnerability(_nvd_parsed())

    assert vulnerability.cve_id == "CVE-2026-0001"
    assert float(vulnerability.cvss_score) == pytest.approx(9.8)
    assert vulnerability.nvd_raw_json["cve"]["id"] == "CVE-2026-0001"

    products = VulnerabilityProduct.objects.filter(vulnerability=vulnerability)
    assert products.count() == 1
    product = products.first()
    assert product.normalized_vendor == "microsoft"
    assert product.normalized_product == "windows server"


@pytest.mark.django_db
def test_upsert_nvd_vulnerability_matches_existing_tag():
    tag = TechTag.objects.create(name="Windows Server", category=TechTagCategory.PRODUCT)

    upsert_nvd_vulnerability(_nvd_parsed())

    product = VulnerabilityProduct.objects.get(normalized_product="windows server")
    assert product.match_status == VulnerabilityProductStatus.MATCHED
    assert product.tech_tag == tag


@pytest.mark.django_db
def test_upsert_nvd_vulnerability_is_idempotent_on_rerun():
    upsert_nvd_vulnerability(_nvd_parsed())
    upsert_nvd_vulnerability(_nvd_parsed(cvss_score=9.9))

    assert Vulnerability.objects.count() == 1
    assert VulnerabilityProduct.objects.count() == 1
    assert float(Vulnerability.objects.get().cvss_score) == pytest.approx(9.9)


@pytest.mark.django_db
def test_upsert_nvd_vulnerability_skips_unparseable_cpe():
    vulnerability = upsert_nvd_vulnerability(
        _nvd_parsed(cpe_list=["not-a-valid-cpe-string"])
    )

    assert VulnerabilityProduct.objects.filter(vulnerability=vulnerability).count() == 0


@pytest.mark.django_db
def test_upsert_kev_status_flags_existing_vulnerability():
    upsert_nvd_vulnerability(_nvd_parsed())

    vulnerability = upsert_kev_status({"cve_id": "CVE-2026-0001", "raw_json": {"cveID": "CVE-2026-0001"}})

    assert vulnerability.is_cisa_kev is True
    assert vulnerability.kev_raw_json["cveID"] == "CVE-2026-0001"


@pytest.mark.django_db
def test_upsert_kev_status_returns_none_for_unknown_cve():
    result = upsert_kev_status({"cve_id": "CVE-2026-9999", "raw_json": {}})

    assert result is None
    assert Vulnerability.objects.count() == 0


@pytest.mark.django_db
def test_upsert_epss_score_updates_existing_vulnerability():
    upsert_nvd_vulnerability(_nvd_parsed())

    vulnerability = upsert_epss_score(
        {"cve_id": "CVE-2026-0001", "epss_score": 0.93, "raw_json": {"cve": "CVE-2026-0001"}}
    )

    assert float(vulnerability.epss_score) == pytest.approx(0.93)
    assert vulnerability.epss_raw_json["cve"] == "CVE-2026-0001"


@pytest.mark.django_db
def test_upsert_epss_score_returns_none_for_unknown_cve():
    result = upsert_epss_score({"cve_id": "CVE-2026-9999", "epss_score": 0.1, "raw_json": {}})

    assert result is None
