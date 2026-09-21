import pytest

from intel.services.ai_prompts import (
    PromptParsingError,
    build_enrichment_prompt,
    parse_enrichment_response,
)


def test_build_enrichment_prompt_includes_all_fields():
    prompt = build_enrichment_prompt(
        title="RCE in Windows Server",
        description="Remote code execution issue",
        cvss_score=9.8,
        epss_score=0.93,
        is_kev=True,
        vendor="microsoft",
        product="windows server",
    )

    assert "Title: RCE in Windows Server" in prompt
    assert "Remote code execution issue" in prompt
    assert "CVSS base score: 9.8" in prompt
    assert "EPSS probability: 0.93" in prompt
    assert "Actively exploited (CISA KEV): yes" in prompt
    assert "Affected product: microsoft windows server" in prompt
    assert "SUMMARY:" in prompt
    assert "REMEDIATION:" in prompt


def test_build_enrichment_prompt_handles_missing_optional_fields():
    prompt = build_enrichment_prompt(
        title="", description="", cvss_score=None, epss_score=None, is_kev=False, vendor="", product=""
    )

    assert "CVSS base score: unknown" in prompt
    assert "EPSS probability: unknown" in prompt
    assert "Actively exploited (CISA KEV): no" in prompt


def test_parse_enrichment_response_extracts_both_sections():
    text = "SUMMARY: Attackers can execute code remotely.\nREMEDIATION: Apply patch KB1234."

    summary, remediation = parse_enrichment_response(text)

    assert summary == "Attackers can execute code remotely."
    assert remediation == "Apply patch KB1234."


def test_parse_enrichment_response_handles_multiline_sections():
    text = "SUMMARY: Line one.\nLine two.\nREMEDIATION: Step one.\nStep two."

    summary, remediation = parse_enrichment_response(text)

    assert summary == "Line one.\nLine two."
    assert remediation == "Step one.\nStep two."


def test_parse_enrichment_response_raises_when_markers_missing():
    with pytest.raises(PromptParsingError):
        parse_enrichment_response("just some unstructured text")


def test_parse_enrichment_response_raises_when_section_empty():
    with pytest.raises(PromptParsingError):
        parse_enrichment_response("SUMMARY: \nREMEDIATION: patch it")
