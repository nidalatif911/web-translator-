"""
Multi-Engine Translation Module
Web Translator
"""

import logging
from deep_translator import MyMemoryTranslator, GoogleTranslator
from app.config import LANGUAGES

logger = logging.getLogger(__name__)


class TranslationService:
    def __init__(self, email: str = "web.translator.service@gmail.com"):
        self.email = email

    def translate(self, text: str, source_lang_name: str, target_lang_name: str) -> str:
        """
        Translates text from source language to target language.
        Uses MyMemoryTranslator as primary with GoogleTranslator as fallback.
        """
        if not text or not text.strip():
            return ""

        clean_text = text.strip()

        # If source and target are the same, no translation needed
        if source_lang_name == target_lang_name:
            return clean_text

        source_info = LANGUAGES.get(source_lang_name)
        target_info = LANGUAGES.get(target_lang_name)

        if not source_info or not target_info:
            raise ValueError(f"Unsupported language pair: {source_lang_name} -> {target_lang_name}")

        # Primary engine: MyMemory
        try:
            translator = MyMemoryTranslator(
                source=source_info["mymemory"],
                target=target_info["mymemory"]
            )
            result = translator.translate(clean_text)
            if result and result.strip():
                return result.strip()
        except Exception as e:
            logger.warning(f"MyMemoryTranslator failed: {e}. Trying Google fallback...")

        # Secondary engine: GoogleTranslator
        try:
            g_translator = GoogleTranslator(
                source=source_info["google"],
                target=target_info["google"]
            )
            result = g_translator.translate(clean_text)
            if result and result.strip():
                return result.strip()
        except Exception as e:
            logger.error(f"GoogleTranslator fallback failed: {e}")

        # If both fail, return original text with warning
        return f"[Translation failed] {clean_text}"


# Singleton instance
translator_service = TranslationService()


def translate_text(text: str, source_lang: str, target_lang: str) -> str:
    """Convenience helper for translation."""
    return translator_service.translate(text, source_lang, target_lang)
