import pytest

from src.app.whatsapp_webhook import _split_for_green_api, GREEN_MAX_MESSAGE_LEN


def test_splitter_under_limit():
    text = "x" * (GREEN_MAX_MESSAGE_LEN - 1)
    parts = _split_for_green_api(text)
    assert parts == [text]


def test_splitter_exact_limit():
    text = "x" * GREEN_MAX_MESSAGE_LEN
    parts = _split_for_green_api(text)
    assert parts == [text]


def test_splitter_over_limit():
    text = "x" * (GREEN_MAX_MESSAGE_LEN + 1)
    parts = _split_for_green_api(text)
    assert len(parts) == 2
    assert parts[0] == "x" * GREEN_MAX_MESSAGE_LEN
    assert parts[1] == "x"


def test_splitter_multiple_chunks():
    text = "x" * (GREEN_MAX_MESSAGE_LEN * 2 + 123)
    parts = _split_for_green_api(text)
    assert len(parts) == 3
    assert all(len(p) <= GREEN_MAX_MESSAGE_LEN for p in parts)
    assert "".join(parts) == text

