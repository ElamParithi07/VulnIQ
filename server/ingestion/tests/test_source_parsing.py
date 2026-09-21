import datetime as dt

import pytest

from intel.models import VulnerabilityStatus
from ingestion.services.source_parsing import (
    SourceParsingError,
    parse_epss_entry,
    parse_kev_entry,
    parse_nvd_entry,
)


def _nvd_entry(**overrides):
    entry = {
        "cve": {
            "id": "CVE-2026-0001",
            "descriptions": [
                {"lang": "es", "value": "no en"},
                {"lang": "en", "value": "Remote code execution issue"},
            ],
            "vulnStatus": "Analyzed",
            "published": "2026-08-01T00:00:00.000",
            "lastModified": "2026-08-08T12:30:00.000",
            "metrics": {
                "cvssMetricV31": [{"cvssData": {"baseScore": 9.8}}],
            },
            "configurations": [
                {
                    "nodes": [
                        {
                            "cpeMatch": [
                                {
                                    "criteria": "cpe:2.3:a:microsoft:windows_server:2019:*:*:*:*:*:*:*",
                                    "vulnerable": True,
                                },
                                {
                                    "criteria": "cpe:2.3:a:microsoft:not_vulnerable_thing:*:*:*:*:*:*:*:*",
                                    "vulnerable": False,
                                },
                            ]
                        }
                    ]
                }
            ],
        }
    }
    entry["cve"].update(overrides)
    return entry


def test_parse_nvd_entry_extracts_expected_fields():
    parsed = parse_nvd_entry(_nvd_entry())

    assert parsed["cve_id"] == "CVE-2026-0001"
    assert parsed["description"] == "Remote code execution issue"
    assert parsed["status"] == VulnerabilityStatus.PUBLISHED
    assert parsed["cvss_score"] == 9.8
    assert parsed["published_at"] == dt.datetime(2026, 8, 1, 0, 0, tzinfo=dt.UTC)
    assert parsed["last_modified_at"] == dt.datetime(2026, 8, 8, 12, 30, tzinfo=dt.UTC)
    assert parsed["cpe_list"] == ["cpe:2.3:a:microsoft:windows_server:2019:*:*:*:*:*:*:*"]
    assert parsed["raw_json"]["cve"]["id"] == "CVE-2026-0001"


@pytest.mark.parametrize(
    "vuln_status,expected",
    [
        ("Rejected", VulnerabilityStatus.REJECTED),
        ("Modified", VulnerabilityStatus.MODIFIED),
        ("Analyzed", VulnerabilityStatus.PUBLISHED),
        ("Awaiting Analysis", VulnerabilityStatus.PUBLISHED),
        (None, VulnerabilityStatus.UNKNOWN),
        ("", VulnerabilityStatus.UNKNOWN),
    ],
)
def test_parse_nvd_entry_maps_status(vuln_status, expected):
    parsed = parse_nvd_entry(_nvd_entry(vulnStatus=vuln_status))

    assert parsed["status"] == expected


def test_parse_nvd_entry_raises_when_cve_id_missing():
    with pytest.raises(SourceParsingError, match="cve.id"):
        parse_nvd_entry({"cve": {}})


def test_parse_kev_entry_extracts_cve_id():
    parsed = parse_kev_entry({"cveID": "CVE-2026-0002", "vendorProject": "Microsoft"})

    assert parsed["cve_id"] == "CVE-2026-0002"
    assert parsed["raw_json"]["vendorProject"] == "Microsoft"


def test_parse_kev_entry_raises_when_cve_id_missing():
    with pytest.raises(SourceParsingError, match="cveID"):
        parse_kev_entry({"vendorProject": "Microsoft"})


def test_parse_epss_entry_extracts_score_as_float():
    parsed = parse_epss_entry({"cve": "CVE-2026-0003", "epss": "0.93210", "percentile": "0.99"})

    assert parsed["cve_id"] == "CVE-2026-0003"
    assert parsed["epss_score"] == pytest.approx(0.9321)


def test_parse_epss_entry_handles_missing_or_invalid_score():
    parsed = parse_epss_entry({"cve": "CVE-2026-0004", "epss": "not-a-number"})

    assert parsed["epss_score"] is None


def test_parse_epss_entry_raises_when_cve_missing():
    with pytest.raises(SourceParsingError, match="cve"):
        parse_epss_entry({"epss": "0.5"})
