from __future__ import annotations

import re

_SEPARATOR_PATTERN = re.compile(r"[_\-/]+")
_WHITESPACE_PATTERN = re.compile(r"\s+")


def normalize_text(value: str) -> str:
    value = value.strip().lower()
    value = _SEPARATOR_PATTERN.sub(" ", value)
    value = _WHITESPACE_PATTERN.sub(" ", value)
    return value.strip()


def remove_vendor_repetition(normalized_vendor: str, normalized_product: str) -> str:
    """Strip a leading run of vendor tokens repeated at the start of the product string.

    Only removes tokens shared from the front, deterministically, so legitimate
    product names are never distorted (e.g. vendor "cisco", product "cisco ios xe"
    becomes "ios xe", but "openssl"/"openssl" is left intact rather than emptied).
    """
    if not normalized_vendor or not normalized_product:
        return normalized_product

    vendor_tokens = normalized_vendor.split()
    product_tokens = normalized_product.split()

    while product_tokens and vendor_tokens and product_tokens[0] == vendor_tokens[0]:
        product_tokens.pop(0)
        vendor_tokens.pop(0)

    cleaned = " ".join(product_tokens).strip()
    return cleaned or normalized_product


def normalize_vendor_product(raw_vendor: str, raw_product: str) -> tuple[str, str]:
    normalized_vendor = normalize_text(raw_vendor)
    normalized_product = remove_vendor_repetition(normalized_vendor, normalize_text(raw_product))
    return normalized_vendor, normalized_product
