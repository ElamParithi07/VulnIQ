from __future__ import annotations


class CPEParseError(Exception):
    """Raised when a CPE string cannot be parsed into vendor/product parts."""


def extract_vendor_product(cpe: str) -> tuple[str, str]:
    """Extract the raw vendor and product segments from a CPE 2.3 formatted string.

    Example: "cpe:2.3:a:microsoft:windows_server:2019:*:*:*:*:*:*:*" -> ("microsoft", "windows_server")
    """
    if not cpe:
        raise CPEParseError("CPE string is empty")

    parts = cpe.split(":")

    if len(parts) < 5 or parts[0] != "cpe" or parts[1] != "2.3":
        raise CPEParseError(f"Unsupported CPE format: {cpe!r}")

    vendor = parts[3]
    product = parts[4]

    if not vendor or not product or vendor == "*" or product == "*":
        raise CPEParseError(f"CPE string is missing vendor/product: {cpe!r}")

    return vendor, product
