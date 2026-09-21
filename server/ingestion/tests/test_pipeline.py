import datetime as dt

import pytest

from ingestion.clients import EPSSClientError, KEVClientError, NVDClientError
from ingestion.models import IngestionRunStatus
from ingestion.services.pipeline import run_ingestion_pipeline
from intel.models import Vulnerability


def _nvd_entry(cve_id: str) -> dict:
    return {
        "cve": {
            "id": cve_id,
            "descriptions": [{"lang": "en", "value": f"Issue in {cve_id}"}],
            "vulnStatus": "Analyzed",
            "published": "2026-08-01T00:00:00.000",
            "lastModified": "2026-08-08T00:00:00.000",
            "metrics": {"cvssMetricV31": [{"cvssData": {"baseScore": 8.1}}]},
            "configurations": [],
        }
    }


class StubNVDClient:
    def __init__(self, entries=None, error=None):
        self.entries = entries or []
        self.error = error

    def fetch_modified_between(self, *, start, end, start_index=0):
        if self.error:
            raise self.error
        return self.entries


class StubKEVClient:
    def __init__(self, entries=None, error=None):
        self.entries = entries or []
        self.error = error

    def fetch_catalog(self):
        if self.error:
            raise self.error
        return self.entries


class StubEPSSClient:
    def __init__(self, entries=None, error=None):
        self.entries = entries or []
        self.error = error
        self.requested_batches = []

    def fetch_scores(self, cve_ids):
        self.requested_batches.append(list(cve_ids))
        if self.error:
            raise self.error
        return [e for e in self.entries if e["cve"] in cve_ids]


NOW = dt.datetime(2026, 8, 9, 0, 0, tzinfo=dt.UTC)


@pytest.mark.django_db
def test_pipeline_happy_path_persists_and_annotates_vulnerability():
    nvd = StubNVDClient(entries=[_nvd_entry("CVE-2026-0001")])
    kev = StubKEVClient(entries=[{"cveID": "CVE-2026-0001"}])
    epss = StubEPSSClient(entries=[{"cve": "CVE-2026-0001", "epss": "0.87"}])

    run = run_ingestion_pipeline(nvd_client=nvd, kev_client=kev, epss_client=epss, now=NOW)

    vulnerability = Vulnerability.objects.get(cve_id="CVE-2026-0001")
    assert float(vulnerability.cvss_score) == pytest.approx(8.1)
    assert vulnerability.is_cisa_kev is True
    assert float(vulnerability.epss_score) == pytest.approx(0.87)

    assert run.status == IngestionRunStatus.SUCCEEDED
    assert run.is_degraded is False
    assert run.nvd_count == 1
    assert run.kev_count == 1
    assert run.epss_count == 1
    assert run.completed_at is not None


@pytest.mark.django_db
def test_pipeline_ignores_kev_entries_outside_this_runs_nvd_set():
    nvd = StubNVDClient(entries=[_nvd_entry("CVE-2026-0001")])
    kev = StubKEVClient(entries=[{"cveID": "CVE-2026-9999"}])
    epss = StubEPSSClient(entries=[])

    run = run_ingestion_pipeline(nvd_client=nvd, kev_client=kev, epss_client=epss, now=NOW)

    assert run.kev_count == 0
    assert Vulnerability.objects.get(cve_id="CVE-2026-0001").is_cisa_kev is False
    assert not Vulnerability.objects.filter(cve_id="CVE-2026-9999").exists()


@pytest.mark.django_db
def test_pipeline_marks_degraded_when_nvd_fails_but_still_completes():
    nvd = StubNVDClient(error=NVDClientError("boom"))
    kev = StubKEVClient(entries=[])
    epss = StubEPSSClient(entries=[])

    run = run_ingestion_pipeline(nvd_client=nvd, kev_client=kev, epss_client=epss, now=NOW)

    assert run.is_degraded is True
    assert "NVD fetch failed" in run.degraded_reason
    assert run.status == IngestionRunStatus.SUCCEEDED
    assert run.nvd_count == 0


@pytest.mark.django_db
def test_pipeline_marks_degraded_when_kev_fails_but_nvd_still_persists():
    nvd = StubNVDClient(entries=[_nvd_entry("CVE-2026-0001")])
    kev = StubKEVClient(error=KEVClientError("kev down"))
    epss = StubEPSSClient(entries=[])

    run = run_ingestion_pipeline(nvd_client=nvd, kev_client=kev, epss_client=epss, now=NOW)

    assert run.is_degraded is True
    assert "KEV fetch failed" in run.degraded_reason
    assert Vulnerability.objects.filter(cve_id="CVE-2026-0001").exists()
    assert run.nvd_count == 1


@pytest.mark.django_db
def test_pipeline_marks_degraded_when_epss_fails():
    nvd = StubNVDClient(entries=[_nvd_entry("CVE-2026-0001")])
    kev = StubKEVClient(entries=[])
    epss = StubEPSSClient(error=EPSSClientError("epss down"))

    run = run_ingestion_pipeline(nvd_client=nvd, kev_client=kev, epss_client=epss, now=NOW)

    assert run.is_degraded is True
    assert "EPSS fetch failed" in run.degraded_reason
    assert run.epss_count == 0


@pytest.mark.django_db
def test_pipeline_accumulates_multiple_degraded_reasons():
    nvd = StubNVDClient(entries=[_nvd_entry("CVE-2026-0001")])
    kev = StubKEVClient(error=KEVClientError("kev down"))
    epss = StubEPSSClient(error=EPSSClientError("epss down"))

    run = run_ingestion_pipeline(nvd_client=nvd, kev_client=kev, epss_client=epss, now=NOW)

    assert run.is_degraded is True
    assert "KEV fetch failed" in run.degraded_reason
    assert "EPSS fetch failed" in run.degraded_reason


@pytest.mark.django_db
def test_pipeline_chunks_epss_requests_over_batch_limit(monkeypatch):
    import ingestion.services.pipeline as pipeline_module

    monkeypatch.setattr(pipeline_module, "MAX_CVE_IDS_PER_REQUEST", 1)

    nvd = StubNVDClient(entries=[_nvd_entry("CVE-2026-0001"), _nvd_entry("CVE-2026-0002")])
    kev = StubKEVClient(entries=[])
    epss = StubEPSSClient(
        entries=[
            {"cve": "CVE-2026-0001", "epss": "0.1"},
            {"cve": "CVE-2026-0002", "epss": "0.2"},
        ]
    )

    run_ingestion_pipeline(nvd_client=nvd, kev_client=kev, epss_client=epss, now=NOW)

    assert epss.requested_batches == [["CVE-2026-0001"], ["CVE-2026-0002"]]
