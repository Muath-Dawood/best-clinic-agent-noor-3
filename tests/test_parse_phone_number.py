import pytest

from src.app.parse_phone_number import parse_whatsapp_to_local_palestinian_number


def test_parse_valid_numbers():
    assert (
        parse_whatsapp_to_local_palestinian_number("972591234567@c.us")
        == "0591234567"
    )
    assert (
        parse_whatsapp_to_local_palestinian_number("0591234567@c.us")
        == "0591234567"
    )
    assert (
        parse_whatsapp_to_local_palestinian_number("972-59 123 4567@c.us")
        == "0591234567"
    )


def test_parse_invalid_numbers():
    assert parse_whatsapp_to_local_palestinian_number("12345@c.us") is None
    assert parse_whatsapp_to_local_palestinian_number("hello") is None


def test_parse_raises_on_non_string():
    with pytest.raises(ValueError):
        parse_whatsapp_to_local_palestinian_number(None)  # type: ignore[arg-type]
