"""
Détection de langue robuste : script arabe d'abord, puis langdetect,
avec mémoire de la dernière langue du chat (anti-oscillation).
"""
import re
from config import DEFAULT_LANGUAGE
from utils import LAST_LANG_CACHE, clean_text, detect_language_simple

_ARABIC_RE = re.compile(r"[\u0600-\u06FF]")


def detect(text: str, chat_id: int | None = None) -> str:
    """Détecte la langue du message. Ordre :
    1. Script arabe prédominant -> "ar"
    2. Message trop court / langdetect échoue -> dernière langue du chat
    3. Sinon langdetect (mappé sur fr/ar/en)
    La langue est mémorisée par chat pour les messages ambigus (« ok », « 1 »).
    """
    text = clean_text(text)
    if not text:
        return DEFAULT_LANGUAGE

    # 1. Script arabe prédominant
    arabic_chars = len(_ARABIC_RE.findall(text))
    if arabic_chars and arabic_chars >= len(text) / 4:
        lang = "ar"
        if chat_id is not None:
            LAST_LANG_CACHE[chat_id] = lang
        return lang

    # 2. Message très court : garder la langue du contexte
    if len(text) <= 3 and chat_id is not None:
        return LAST_LANG_CACHE.get(chat_id, DEFAULT_LANGUAGE)

    # 3. Détection langdetect
    lang = detect_language_simple(text)
    if chat_id is not None:
        LAST_LANG_CACHE[chat_id] = lang
    return lang
