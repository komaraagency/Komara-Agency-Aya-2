"""
Routeur de messages : découpe la logique de _process_text en fonctions modulaires.
Chaîne de responsabilité pour traiter les messages dans le bon ordre.
"""
import re
from utils import clean_text, is_secret_probe, GENERIC_MESSAGES
from language_detector import detect_language, get_language
from pending_question import get_pending, is_valid_answer, clear_pending
from logical_steps import process_devis_step, get_flow_state
from farewell_guard import is_farewell, get_farewell_response
from sector_reply import get_sector_response
import rag_engine


def route_message(chat_id: int, user_text: str, bot_send_func) -> bool:
    """
    Route un message texte vers le bon handler.

    Args:
        chat_id: ID du chat
        user_text: Texte du message
        bot_send_func: Fonction pour envoyer une réponse (bot.send_message)

    Returns:
        True si le message a été traité, False sinon
    """
    # 1. Nettoyage
    text = clean_text(user_text)
    if not text:
        return False

    # 2. Détection de langue
    lang = detect_language(text, chat_id)

    # 3. Sécurité : bloquer les tentatives d'extraction de prompts
    if is_secret_probe(text):
        bot_send_func(chat_id, GENERIC_MESSAGES[lang]["secret_blocked"])
        return True

    # 4. Vérifier les adieux
    if is_farewell(text, lang):
        bot_send_func(chat_id, get_farewell_response(lang))
        return True

    # 5. Vérifier les questions en attente
    pending = get_pending(chat_id)
    if pending:
        is_valid, answer = is_valid_answer(chat_id, text)
        if is_valid:
            # Traiter la réponse
            flow_response = process_devis_step(chat_id, text, lang)
            if flow_response:
                bot_send_func(chat_id, flow_response)
                return True

    # 6. Vérifier les flux actifs (devis, etc.)
    flow = get_flow_state(chat_id)
    if flow:
        flow_response = process_devis_step(chat_id, text, lang)
        if flow_response:
            bot_send_func(chat_id, flow_response)
            return True

    # 7. Recherche RAG avec détection de secteur
    rag_response = get_sector_response(text, lang)
    if rag_response:
        bot_send_func(chat_id, rag_response)
        return True

    # 8. Fallback : message générique
    bot_send_func(chat_id, GENERIC_MESSAGES[lang]["no_understand"])
    return True


def handle_punctuation_only(text: str) -> bool:
    """Vérifie si le message ne contient que de la ponctuation."""
    cleaned = re.sub(r'[^\w\s]', '', text)
    return len(cleaned.strip()) == 0


def handle_greeting(text: str, lang: str) -> str | None:
    """Détecte et répond aux salutations."""
    greetings = {
        "fr": ["bonjour", "hello", "salut", "hi", "coucou"],
        "ar": ["مرحبا", "السلام", "اهلا", "سلام"],
        "en": ["hello", "hi", "hey", "good morning", "good afternoon"],
    }

    text_lower = text.lower()
    for greeting in greetings.get(lang, []):
        if greeting in text_lower:
            return GENERIC_MESSAGES[lang]["greeting"]

    return None
