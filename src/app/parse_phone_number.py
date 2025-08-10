def parse_whatsapp_to_local_palestinian_number(chat_id: str) -> str:
    """
    Turn a WhatsApp chatId like '97259XXXXXXX@c.us' into '059XXXXXXX'.
    Keeps other formats best‑effort.
    """
    raw = chat_id.split("@", 1)[0]
    if raw.startswith("972"):
        return "0" + raw[3:]
    return raw
