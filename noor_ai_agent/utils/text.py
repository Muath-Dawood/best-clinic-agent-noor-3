"""
Text processing utilities.
"""

import re
from typing import List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class TextExtractionResult:
    """Result of text extraction from WhatsApp message."""
    text: str
    had_attachments: bool


class TextProcessor:
    """Text processing utilities."""

    @staticmethod
    def normalize_arabic_text(text: str) -> str:
        """Normalize Arabic text for matching."""
        if not isinstance(text, str):
            text = str(text or "")

        text = text.strip()
        text = text.replace("•", " ").replace("·", " ").strip()
        text = re.sub("[ًٌٍَُِّْـ]", "", text)
        text = text.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
        text = text.replace("ى", "ي").replace("ة", "ه")
        return re.sub(r"\s+", " ", text).lower()

    @staticmethod
    def clean_whatsapp_text(text: str) -> str:
        """Clean WhatsApp text by removing file references."""
        if not text:
            return ""

        ar_keywords = ("ملف", "ملفات", "مرفق", "مرفقات", "المرفوع")
        en_keywords = (
            "file", "files", "upload", "uploads",
            "attachment", "attachments", "document", "documents"
        )

        lines = []
        for line in text.splitlines():
            line_lower = line.lower()
            if any(keyword in line_lower for keyword in en_keywords):
                continue
            if any(keyword in line for keyword in ar_keywords):
                continue
            lines.append(line)

        return "\n".join(lines).strip()

    @staticmethod
    def split_text_for_whatsapp(text: str, max_length: int = 4096) -> List[str]:
        """Split text into chunks suitable for WhatsApp."""
        if len(text) <= max_length:
            return [text]

        chunks = []
        current_chunk = ""

        for word in text.split():
            if len(current_chunk + " " + word) <= max_length:
                current_chunk += (" " + word) if current_chunk else word
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = word

        if current_chunk:
            chunks.append(current_chunk)

        return chunks


class WhatsAppTextExtractor:
    """Extract text from WhatsApp webhook payload."""

    @staticmethod
    def extract_text_from_wa(body: dict) -> TextExtractionResult:
        """Extract text from WhatsApp webhook body."""
        text_in = ""
        had_attach = False

        # Check for text message
        if "messageData" in body:
            message_data = body["messageData"]
            if isinstance(message_data, dict):
                text_in = message_data.get("textMessageData", {}).get("textMessage", "")
            elif isinstance(message_data, str):
                text_in = message_data

        # Check for attachments
        if "messageData" in body:
            message_data = body["messageData"]
            if isinstance(message_data, dict):
                had_attach = any(
                    key in message_data
                    for key in ["documentMessageData", "imageMessageData", "videoMessageData"]
                )

        return TextExtractionResult(
            text=text_in.strip() if text_in else "",
            had_attachments=had_attach
        )
