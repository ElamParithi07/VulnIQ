import pytest

from intel.services.cpe import CPEParseError, extract_vendor_product


def test_extracts_vendor_and_product_from_cpe23_string():
    vendor, product = extract_vendor_product(
        "cpe:2.3:a:microsoft:windows_server:2019:*:*:*:*:*:*:*"
    )

    assert vendor == "microsoft"
    assert product == "windows_server"


def test_extracts_vendor_and_product_for_cisco_example():
    vendor, product = extract_vendor_product("cpe:2.3:o:cisco:ios_xe:*:*:*:*:*:*:*:*")

    assert vendor == "cisco"
    assert product == "ios_xe"


@pytest.mark.parametrize(
    "cpe",
    [
        "",
        "not-a-cpe-string",
        "cpe:2.2:a:microsoft:windows_server",
        "cpe:2.3:a:*:windows_server:2019:*:*:*:*:*:*:*",
        "cpe:2.3:a:microsoft:*:2019:*:*:*:*:*:*:*",
    ],
)
def test_raises_on_malformed_or_wildcard_cpe(cpe):
    with pytest.raises(CPEParseError):
        extract_vendor_product(cpe)
