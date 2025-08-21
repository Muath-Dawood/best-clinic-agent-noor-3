from typing import Any, Tuple, List

MAX_WA_BYTES = 3500  # adjust to your sender’s hard limit headroom

def extract_text_from_wa(body: dict) -> Tuple[str, bool]:
    """
    Returns (text, had_attachments). Supports textMessageData, extendedTextMessageData,
    and flags when message is non-text (images/docs).
    """
    try:
        msg = body.get("messageData") or {}
        txt = (msg.get("textMessageData") or {}).get("textMessage")
        if not txt:
            txt = (msg.get("extendedTextMessageData") or {}).get("text")
        if isinstance(txt, str) and txt.strip():
            return txt.strip(), False
        # Non-text?
        if msg.get("fileMessageData") or msg.get("imageMessageData") or msg.get("videoMessageData"):
            return "", True
    except Exception:
        pass
    return "", False

def split_for_whatsapp_by_bytes(text: str, max_bytes: int = MAX_WA_BYTES) -> List[str]:
    """
    Splits on UTF-8 byte boundaries, not char count — avoids breaking emoji/diacritics.
    Prefers splitting on whitespace; falls back to hard byte cut.
    """
    chunks, buf = [], ""
    for token in text.split(" "):
        tentative = (buf + (" " if buf else "") + token) if token else buf
        if len(tentative.encode("utf-8")) <= max_bytes:
            buf = tentative
            continue
        if buf:
            chunks.append(buf)
            buf = token
            if buf:
                buf = " " + buf
        else:
            # single token too large; hard split
            b = token.encode("utf-8")
            start = 0
            while start < len(b):
                end = min(start + max_bytes, len(b))
                # safe decode slice
                piece = b[start:end]
                while True:
                    try:
                        chunks.append(piece.decode("utf-8"))
                        break
                    except UnicodeDecodeError:
                        end -= 1
                        piece = b[start:end]
                start = end
            buf = ""
    if buf:
        chunks.append(buf)
    return chunks
