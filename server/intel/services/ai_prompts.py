from __future__ import annotations

import re

PROMPT_VERSION = "v1"

_PROMPT_TEMPLATE = """You are a cybersecurity threat intelligence assistant. Given the vulnerability \
details below, produce two outputs for a business audience.

Vulnerability details:
- Title: {title}
- Description: {description}
- CVSS base score: {cvss_score}
- EPSS probability: {epss_score}
- Actively exploited (CISA KEV): {is_kev}
- Affected product: {vendor} {product}

Output rules:
- Risk summary: maximum two sentences, concise, operationally clear, business-friendly. Do not \
mention the CVE ID.
- Remediation: short technical guidance, followed by commands or configuration examples only when \
clearly applicable. No long prose. If product-specific remediation is unclear, give conservative \
generic guidance instead of inventing specific commands.

Respond in exactly this format with no extra commentary:
SUMMARY: <risk summary text>
REMEDIATION: <remediation text>
"""

_SUMMARY_PATTERN = re.compile(r"SUMMARY:[ \t]*(.*?)(?=\r?\nREMEDIATION:|\Z)", re.DOTALL)
_REMEDIATION_PATTERN = re.compile(r"REMEDIATION:[ \t]*(.*)", re.DOTALL)


class PromptParsingError(Exception):
    """Raised when a Gemini response does not match the expected output contract."""


def build_enrichment_prompt(
    *,
    title: str,
    description: str,
    cvss_score,
    epss_score,
    is_kev: bool,
    vendor: str,
    product: str,
) -> str:
    return _PROMPT_TEMPLATE.format(
        title=title or "Unknown",
        description=description or "No description available.",
        cvss_score=cvss_score if cvss_score is not None else "unknown",
        epss_score=epss_score if epss_score is not None else "unknown",
        is_kev="yes" if is_kev else "no",
        vendor=vendor or "unknown vendor",
        product=product or "unknown product",
    )


def parse_enrichment_response(text: str) -> tuple[str, str]:
    summary_match = _SUMMARY_PATTERN.search(text)
    remediation_match = _REMEDIATION_PATTERN.search(text)

    if not summary_match or not remediation_match:
        raise PromptParsingError("Response did not match the expected SUMMARY/REMEDIATION format")

    summary = summary_match.group(1).strip()
    remediation = remediation_match.group(1).strip()

    if not summary or not remediation:
        raise PromptParsingError("Response contained an empty summary or remediation section")

    return summary, remediation
