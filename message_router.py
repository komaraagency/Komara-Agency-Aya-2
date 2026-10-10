"""
Routeur de messages découplé.
Contient TOUTE la logique de décision (sans I/O Telegram) :
worker.py ne fait qu'entrées/sorties.

Chaîne de décision :
1. Question en attente (flux devis / choix portfolio) -> réponse du flux
2. Sonde de secrets -> blocage poli
3. Adieu / remerciement -> réponse d'adieu (ne relance pas)
4. Commandes simples (services, devis, portfolio, tarifs, start)
5. Réponse sectorielle + RAG dans la LANGUE du client
6. Repli : message générique DANS SA LANGUE (jamais de fallback FR)
"""
import re
from config import DEFAULT_LANGUAGE
from utils import (
    GENERIC_MESSAGES, LAST_LANG_CACHE, clean_text, is_secret_probe,
    is_single_digit,
)
import language_detector
import farewell_guard
import logical_steps
import sector_reply
import portfolio_drive
from pending_question import set_pending, get_pending, clear_pending

_CMD = re.compile(r"^/(start|help)", re.IGNORECASE)


def _start_message(lang: str) -> str:
    return GENERIC_MESSAGES[lang]["greeting"]


def _portfolio_selected(chat_id: int, text: str, lang: str) -> str | None:
    """Le client a choisi un numéro/titre après la liste portfolio."""
    pending = get_pending(chat_id)
    if not pending or pending.get("context") != "portfolio":
        return None
    choice = portfolio_drive.pick(text)
    clear_pending(chat_id)
    if choice is None:
        set_pending(chat_id, "choice", "portfolio")
        asks = {
            "fr": "Je n'ai pas trouvé cette réalisation. Choisis un numéro ou un titre de la liste 👇",
            "ar": "لم أجد هذا العمل. اختر رقما أو عنوانا من القائمة 👇",
            "en": "I couldn't find that piece. Pick a number or title from the list 👇",
        }
        return asks.get(lang, asks["fr"])
    title, url = choice
    found = {
        "fr": f" Voilà « {title} » 👉 {url}\n\nUne autre réalisation t'intéresse ? Numéro ou titre 👇",
        "ar": f" هذا « {title} » 👉 {url}\n\nهل يهمك عمل آخر؟ رقم أو عنوان 👇",
        "en": f" Here's “{title}” 👉 {url}\n\nInterested in another piece? Number or title 👇",
    }
    set_pending(chat_id, "choice", "portfolio")
    return found.get(lang, found["fr"])


def route(chat_id: int, user_text: str, user_name: str = "") -> tuple[str, str]:
    """Point d'entrée unique. Retourne (réponse, langue)."""
    if _CMD.match(user_text or ""):
        lang = LAST_LANG_CACHE.get(chat_id, DEFAULT_LANGUAGE)
        return _start_message(lang), lang

    text = clean_text(user_text)
    lang = language_detector.detect(text, chat_id)
    low = text.lower()

    # 1. Question en attente : flux devis
    flow_reply = logical_steps.process_devis_step(chat_id, text, lang)
    if flow_reply is not None:
        return flow_reply, lang

    # 1bis. Question en attente : choix portfolio
    if get_pending(chat_id) and get_pending(chat_id).get("context") == "portfolio":
        picked = _portfolio_selected(chat_id, text, lang)
        if picked:
            return picked, lang

    # 2. Sonde de secrets (prompt système, code source...)
    if is_secret_probe(text):
        return GENERIC_MESSAGES[lang]["secret_blocked"], lang

    # 3. Adieu / remerciement : on ne relance pas
    if farewell_guard.is_farewell(text, lang):
        clear_pending(chat_id)
        logical_steps.clear_flow_state(chat_id)
        return farewell_guard.get_farewell_response(lang), lang

    # 4. Commandes simples
    if re.search(r"\b(devis|quote)\b", low):
        return logical_steps.start_devis_flow(chat_id, lang), lang
    if re.search(r"\b(portfolio|réalisations|realisations|catalogue|portfolio|أعمال)\b", low) \
            or (lang == "ar" and "أعمال" in low):
        listing = portfolio_drive.numbered_list(lang)
        if listing:
            set_pending(chat_id, "choice", "portfolio")
            return listing, lang
        unavailable = {
            "fr": "Portfolio indisponible pour le moment. Réessaie plus tard 🙂",
            "ar": "معرض الأعمال غير متوفر حاليا. حاول لاحقا 🙂",
            "en": "Portfolio unavailable right now. Try again later 🙂",
        }
        return unavailable.get(lang, unavailable["fr"]), lang

    # 5. Réponse sectorielle + RAG (dans la langue du client, pas de repli)
    reply = sector_reply.get_sector_response(text, lang)
    if reply:
        return reply, lang

    # 6. Repli générique dans la langue du client
    return GENERIC_MESSAGES[lang]["no_understand"], lang
