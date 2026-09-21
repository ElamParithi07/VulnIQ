import pytest

from intel.models import Vulnerability, VulnerabilityProduct, VulnerabilityProductStatus
from intel.services.matching import match_vulnerability_product, resolve_tech_tag
from taxonomy.models import TechTag, TechTagAlias, TechTagCategory


def _create_product(**kwargs) -> VulnerabilityProduct:
    vulnerability = Vulnerability.objects.create(cve_id=kwargs.pop("cve_id", "CVE-2026-0001"))
    defaults = {
        "raw_vendor": "Microsoft",
        "raw_product": "Windows Server",
        "normalized_vendor": "microsoft",
        "normalized_product": "windows server",
    }
    defaults.update(kwargs)
    return VulnerabilityProduct.objects.create(vulnerability=vulnerability, **defaults)


@pytest.mark.django_db
def test_resolve_matches_exact_alias():
    tag = TechTag.objects.create(name="Windows Server", category=TechTagCategory.PRODUCT)
    TechTagAlias.objects.create(tag=tag, alias="win server")

    status, matched_tag = resolve_tech_tag("win server")

    assert status == VulnerabilityProductStatus.MATCHED
    assert matched_tag == tag


@pytest.mark.django_db
def test_resolve_matches_canonical_tag_name_when_no_alias():
    tag = TechTag.objects.create(name="VMware vCenter", category=TechTagCategory.PRODUCT)

    status, matched_tag = resolve_tech_tag("vmware vcenter")

    assert status == VulnerabilityProductStatus.MATCHED
    assert matched_tag == tag


@pytest.mark.django_db
def test_alias_match_takes_precedence_over_canonical_name():
    canonical_tag = TechTag.objects.create(name="apache http server", category=TechTagCategory.PRODUCT)
    alias_owner_tag = TechTag.objects.create(name="Apache HTTPD", category=TechTagCategory.PRODUCT)
    TechTagAlias.objects.create(tag=alias_owner_tag, alias="apache http server")

    status, matched_tag = resolve_tech_tag("apache http server")

    assert status == VulnerabilityProductStatus.MATCHED
    assert matched_tag == alias_owner_tag
    assert matched_tag != canonical_tag


@pytest.mark.django_db
def test_resolve_returns_unmatched_when_nothing_found():
    status, matched_tag = resolve_tech_tag("totally unknown product")

    assert status == VulnerabilityProductStatus.UNMATCHED
    assert matched_tag is None


@pytest.mark.django_db
def test_resolve_ignores_inactive_tags():
    TechTag.objects.create(name="Deprecated Tool", category=TechTagCategory.PRODUCT, is_active=False)

    status, matched_tag = resolve_tech_tag("deprecated tool")

    assert status == VulnerabilityProductStatus.UNMATCHED
    assert matched_tag is None


@pytest.mark.django_db
def test_match_vulnerability_product_persists_matched_tag():
    tag = TechTag.objects.create(name="Windows Server", category=TechTagCategory.PRODUCT)
    product = _create_product(normalized_product="windows server")

    updated = match_vulnerability_product(product)
    product.refresh_from_db()

    assert updated.match_status == VulnerabilityProductStatus.MATCHED
    assert updated.tech_tag == tag
    assert product.tech_tag == tag
    assert product.match_status == VulnerabilityProductStatus.MATCHED


@pytest.mark.django_db
def test_match_vulnerability_product_persists_unmatched_with_no_tag():
    product = _create_product(normalized_product="unknown thing")

    updated = match_vulnerability_product(product)

    assert updated.match_status == VulnerabilityProductStatus.UNMATCHED
    assert updated.tech_tag is None


@pytest.mark.django_db
def test_match_vulnerability_product_skips_ignored_products():
    product = _create_product(
        normalized_product="windows server",
        match_status=VulnerabilityProductStatus.IGNORED,
    )
    TechTag.objects.create(name="Windows Server", category=TechTagCategory.PRODUCT)

    updated = match_vulnerability_product(product)

    assert updated.match_status == VulnerabilityProductStatus.IGNORED
    assert updated.tech_tag is None
