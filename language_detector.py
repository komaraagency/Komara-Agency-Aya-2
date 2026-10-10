"""
Détection de langue améliorée avec gestion des caractères arabes.
"""
import re
from utils import detect_language_simple, LAST_LANG_CACHE


def detect_language(text: str, chat_id: int = None) -> str:
    """
    Détecte la langue d'un message.
    Utilise le cache pour éviter de re-détecter à chaque message.
    """
    # Vérifier le cache
    if chat_id and chat_id in LAST_LANG_CACHE:
        return LAST_LANG_CACHE[chat_id]

    # Détection simple
    lang = detect_language_simple(text)

    # Détection spécifique pour l'arabe (caractères Unicode)
    arabic_pattern = re.compile(r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]')
    if arabic_pattern.search(text):
        lang = "ar"

    # Mettre en cache
    if chat_id:
        LAST_LANG_CACHE[chat_id] = lang

    return lang


def change_language(chat_id: int, new_lang: str):
    """Change la langue préférée d'un chat."""
    LAST_LANG_CACHE[chat_id] = new_lang


def get_language(chat_id: int) -> str:
    """Récupère la langue actuelle d'un chat."""
    from config import DEFAULT_LANGUAGE
    return LAST_LANG_CACHE.get(chat_id, DEFAULT_LANGUAGE)
