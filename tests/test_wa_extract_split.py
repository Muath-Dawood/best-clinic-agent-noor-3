from src.app.utils_text import extract_text_from_wa, split_for_whatsapp_by_bytes


def test_extract_text_variants():
    body1 = {"messageData": {"textMessageData": {"textMessage": "hi"}}}
    body2 = {"messageData": {"extendedTextMessageData": {"text": "hello"}}}
    body3 = {"messageData": {"imageMessageData": {"caption": "photo"}}}
    assert extract_text_from_wa(body1) == ("hi", False)
    assert extract_text_from_wa(body2) == ("hello", False)
    txt, had = extract_text_from_wa(body3)
    assert txt == "" and had is True


def test_splitter_preserves_emoji_boundaries():
    s = "مرحبا 😊" * 1000
    chunks = split_for_whatsapp_by_bytes(s, max_bytes=500)
    assert all(len(c.encode("utf-8")) <= 500 for c in chunks)
    assert "".join(chunks).strip() == s.strip()
