"""
Détection et gestion des questions en attente.
Utilise un système d'état (State Machine) au lieu de regex fragiles.
"""
import time
from utils import PENDING_QUESTIONS


# === Types de questions en attente ===
PENDING_TYPES = {
    "confirmation": ["oui", "non", "yes", "no", "نعم", "لا"],
    "choice": ["1", "2", "3", "4", "5", "6", "7", "8", "9"],
    "open": [],  # Question ouverte, n'importe quelle réponse est valide
}


def set_pending(chat_id: int, question_type: str, context: str = ""):
    """
    Marque qu'une question est en attente pour un chat.

    Args:
        chat_id: ID du chat
        question_type: "confirmation", "choice", ou "open"
        context: Contexte additionnel (ex: "tarifs", "rdv")
    """
    PENDING_QUESTIONS[chat_id] = {
        "type": question_type,
        "context": context,
        "set_at": time.time(),
    }


def get_pending(chat_id: int) -> dict | None:
    """Récupère la question en attente pour un chat, ou None."""
    pending = PENDING_QUESTIONS.get(chat_id)
    if pending is None:
        return None

    # Expirer après 10 minutes
    if time.time() - pending.get("set_at", 0) > 600:
        clear_pending(chat_id)
        return None

    return pending


def clear_pending(chat_id: int):
    """Efface la question en attente pour un chat."""
    if chat_id in PENDING_QUESTIONS:
        del PENDING_QUESTIONS[chat_id]


def is_valid_answer(chat_id: int, user_text: str) -> tuple[bool, str]:
    """
    Vérifie si la réponse du client est valide pour la question en attente.

    Returns:
        (is_valid, normalized_answer)
    """
    pending = get_pending(chat_id)
    if pending is None:
        return False, ""

    text_lower = user_text.strip().lower()
    q_type = pending["type"]

    if q_type == "confirmation":
        if text_lower in ["oui", "yes", "نعم", "ok", "d'accord"]:
            return True, "oui"
        elif text_lower in ["non", "no", "لا", "nop", "nope"]:
            return True, "non"
        return False, ""

    elif q_type == "choice":
        from utils import is_single_digit
        is_digit, num = is_single_digit(user_text)
        if is_digit:
            return True, str(num)
        return False, ""

    elif q_type == "open":
        return True, user_text

    return False, ""
