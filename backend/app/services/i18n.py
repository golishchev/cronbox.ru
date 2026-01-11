"""Internationalization service for backend translations."""
import json
from functools import lru_cache
from pathlib import Path

import structlog

logger = structlog.get_logger()

LOCALES_DIR = Path(__file__).parent.parent / "locales"
DEFAULT_LANGUAGE = "en"
SUPPORTED_LANGUAGES = {"en", "ru"}


@lru_cache(maxsize=10)
def _load_locale(lang: str) -> dict:
    """Load locale file for a language."""
    locale_file = LOCALES_DIR / f"{lang}.json"
    if not locale_file.exists():
        logger.warning("Locale file not found", lang=lang)
        return {}

    with open(locale_file, "r", encoding="utf-8") as f:
        return json.load(f)


def get_translation(key: str, lang: str = DEFAULT_LANGUAGE, **kwargs) -> str:
    """
    Get a translation by key path (e.g., "notifications.test.telegram_title").

    Args:
        key: Dot-separated path to the translation key
        lang: Language code (e.g., "ru", "en")
        **kwargs: Variables to format into the translation string

    Returns:
        Translated and formatted string, or the key if not found
    """
    if lang not in SUPPORTED_LANGUAGES:
        lang = DEFAULT_LANGUAGE

    translations = _load_locale(lang)

    # Navigate through nested keys
    value = translations
    for part in key.split("."):
        if isinstance(value, dict) and part in value:
            value = value[part]
        else:
            # Key not found, try fallback language
            if lang != DEFAULT_LANGUAGE:
                return get_translation(key, DEFAULT_LANGUAGE, **kwargs)
            logger.warning("Translation key not found", key=key, lang=lang)
            return key

    if not isinstance(value, str):
        return key

    # Format with provided variables
    if kwargs:
        try:
            value = value.format(**kwargs)
        except KeyError as e:
            logger.warning("Missing translation variable", key=key, missing=str(e))

    return value


def t(key: str, lang: str = DEFAULT_LANGUAGE, **kwargs) -> str:
    """Shortcut for get_translation."""
    return get_translation(key, lang, **kwargs)


class I18nService:
    """Service class for translations with a fixed language."""

    def __init__(self, lang: str = DEFAULT_LANGUAGE):
        self.lang = lang if lang in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE

    def t(self, key: str, **kwargs) -> str:
        """Get translation for the configured language."""
        return get_translation(key, self.lang, **kwargs)


def get_i18n(lang: str) -> I18nService:
    """Create an I18nService instance for a specific language."""
    return I18nService(lang)
