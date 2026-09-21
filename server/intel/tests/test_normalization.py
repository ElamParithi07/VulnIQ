from intel.services.normalization import (
    normalize_text,
    normalize_vendor_product,
    remove_vendor_repetition,
)


def test_normalize_text_lowercases_trims_and_collapses_separators():
    assert normalize_text("  Cisco_IOS-XE/17  ") == "cisco ios xe 17"


def test_normalize_text_collapses_repeated_whitespace():
    assert normalize_text("Windows   Server") == "windows server"


def test_remove_vendor_repetition_strips_leading_vendor_tokens():
    assert remove_vendor_repetition("cisco", "cisco ios xe") == "ios xe"


def test_remove_vendor_repetition_strips_multiple_leading_shared_tokens():
    assert (
        remove_vendor_repetition("microsoft corporation", "microsoft windows server")
        == "windows server"
    )


def test_remove_vendor_repetition_is_noop_when_no_overlap():
    assert remove_vendor_repetition("apache", "http server") == "http server"


def test_remove_vendor_repetition_falls_back_when_product_would_become_empty():
    assert remove_vendor_repetition("openssl", "openssl") == "openssl"


def test_normalize_vendor_product_end_to_end():
    vendor, product = normalize_vendor_product("Cisco", "cisco_ios_xe")

    assert vendor == "cisco"
    assert product == "ios xe"
