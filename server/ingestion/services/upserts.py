from __future__ import annotations

from typing import Any

from django.utils import timezone

from intel.models import Vulnerability, VulnerabilityProduct
from intel.services.cpe import CPEParseError, extract_vendor_product
from intel.services.matching import match_vulnerability_product
from intel.services.normalization import normalize_vendor_product


def upsert_nvd_vulnerability(parsed: dict[str, Any]) -> Vulnerability:
    vulnerability, _created = Vulnerability.objects.update_or_create(
        cve_id=parsed["cve_id"],
        defaults={
            "title": parsed.get("title", ""),
            "description": parsed.get("description", ""),
            "status": parsed.get("status"),
            "cvss_score": parsed.get("cvss_score"),
            "published_at": parsed.get("published_at"),
            "last_modified_at": parsed.get("last_modified_at"),
            "last_seen_in_feed_at": timezone.now(),
            "nvd_raw_json": parsed.get("raw_json", {}),
        },
    )
    _sync_products(vulnerability, parsed.get("cpe_list", []))
    return vulnerability


def _sync_products(vulnerability: Vulnerability, cpe_list: list[str]) -> None:
    for cpe in cpe_list:
        try:
            raw_vendor, raw_product = extract_vendor_product(cpe)
        except CPEParseError:
            continue

        normalized_vendor, normalized_product = normalize_vendor_product(raw_vendor, raw_product)

        product, _created = VulnerabilityProduct.objects.update_or_create(
            vulnerability=vulnerability,
            normalized_vendor=normalized_vendor,
            normalized_product=normalized_product,
            defaults={
                "raw_vendor": raw_vendor,
                "raw_product": raw_product,
                "source_cpe": cpe,
            },
        )
        match_vulnerability_product(product)


def upsert_kev_status(parsed: dict[str, Any]) -> Vulnerability | None:
    try:
        vulnerability = Vulnerability.objects.get(cve_id=parsed["cve_id"])
    except Vulnerability.DoesNotExist:
        return None

    vulnerability.is_cisa_kev = True
    vulnerability.kev_raw_json = parsed.get("raw_json", {})
    vulnerability.save(update_fields=["is_cisa_kev", "kev_raw_json", "updated_at"])
    return vulnerability


def upsert_epss_score(parsed: dict[str, Any]) -> Vulnerability | None:
    try:
        vulnerability = Vulnerability.objects.get(cve_id=parsed["cve_id"])
    except Vulnerability.DoesNotExist:
        return None

    vulnerability.epss_score = parsed.get("epss_score")
    vulnerability.epss_raw_json = parsed.get("raw_json", {})
    vulnerability.save(update_fields=["epss_score", "epss_raw_json", "updated_at"])
    return vulnerability
