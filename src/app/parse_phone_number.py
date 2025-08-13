import re
from typing import Optional


def parse_whatsapp_to_local_palestinian_number(chat_id: str) -> Optional[str]:
    """
    Turn a WhatsApp chatId like '97259XXXXXXX@c.us' into '059XXXXXXX'.
    Non-digit characters are stripped before validation.
    Returns the sanitized number in local format or ``None`` if invalid.

    Raises:
        ValueError: If ``chat_id`` is not a string.
    """
    if not isinstance(chat_id, str):
        raise ValueError("chat_id must be a string")

    raw = chat_id.split("@", 1)[0]
    digits = re.sub(r"\D", "", raw)

    if digits.startswith("972"):
        digits = "0" + digits[3:]

    if re.fullmatch(r"05\d{8}", digits):
        return digits

    return None
