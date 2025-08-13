from src.app.output_sanitizer import redact_tokens


def test_redact_tokens_replaces_known_patterns():
    text = (
        "Use svc123 and emp456 then token ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 for debugging"
    )
    result = redact_tokens(text)
    assert "svc123" not in result
    assert "emp456" not in result
    assert "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789" not in result
    assert result.count("[REDACTED]") == 3


def test_redact_tokens_without_patterns():
    text = "Hello world"
    assert redact_tokens(text) == text
