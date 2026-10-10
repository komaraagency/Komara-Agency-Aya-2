"""
Étapes logiques de conversation (flux commerciaux).
Gère les séquences : devis -> services -> tarifs -> confirmation.
"""
import time
from pending_question import set_pending, clear_pending

# === États du flux ===
FLOW_STATES = {}


def set_flow_state(chat_id: int, state: str, data: dict = None):
    """Définit l'état du flux pour un chat."""
    FLOW_STATES[chat_id] = {
        "state": state,
        "data": data or {},
        "updated_at": time.time(),
    }


def get_flow_state(chat_id: int) -> dict | None:
    """Récupère l'état du flux pour un chat."""
    state = FLOW_STATES.get(chat_id)
    if state is None:
        return None
    # Expirer après 30 minutes
    if time.time() - state.get("updated_at", 0) > 1800:
        clear_flow_state(chat_id)
        return None
    return state


def clear_flow_state(chat_id: int):
    """Efface l'état du flux pour un chat."""
    if chat_id in FLOW_STATES:
        del FLOW_STATES[chat_id]


# === Flux de conversation ===
def start_devis_flow(chat_id: int, lang: str) -> str:
    """Démarre le flux de demande de devis."""
    set_flow_state(chat_id, "devis_services", {})

    messages = {
        "fr": "Parfait ! Pour vous préparer un devis, quels services vous intéressent ?\n\n1️⃣ Design intérieur\n2️⃣ Architecture\n3️⃣ Rénovation\n4️⃣ Consultation\n\nRépondez avec le numéro.",
        "ar": "ممتاز! لتحضير عرض سعر، ما هي الخدمات التي تهمك؟\n\n1️⃣ تصميم داخلي\n2️⃣ هندسة معمارية\n3️⃣ ترميم\n4️⃣ استشارة\n\nأجب بالرقم.",
        "en": "Great! To prepare a quote, which services interest you?\n\n1️⃣ Interior Design\n2️⃣ Architecture\n3️⃣ Renovation\n4️⃣ Consultation\n\nReply with the number.",
    }
    set_pending(chat_id, "choice", "devis_services")
    return messages.get(lang, messages["fr"])


def process_devis_step(chat_id: int, user_text: str, lang: str) -> str | None:
    """Traite une étape du flux de devis. Retourne None si pas dans un flux."""
    flow = get_flow_state(chat_id)
    if flow is None:
        return None

    state = flow["state"]

    if state == "devis_services":
        from utils import is_single_digit
        is_digit, num = is_single_digit(user_text)
        if not is_digit:
            messages = {
                "fr": "Veuillez répondre avec un numéro entre 1 et 4.",
                "ar": "يرجى الرد برقم بين 1 و 4.",
                "en": "Please reply with a number between 1 and 4.",
            }
            return messages.get(lang, messages["fr"])

        services = {1: "Design intérieur", 2: "Architecture", 3: "Rénovation", 4: "Consultation"}
        flow["data"]["service"] = services.get(num, "Autre")
        set_flow_state(chat_id, "devis_budget", flow["data"])

        messages = {
            "fr": f"Vous avez choisi : {services[num]}. Quel est votre budget approximatif ?",
            "ar": f"لقد اخترت: {services[num]}. ما هي ميزانيتك التقريبية؟",
            "en": f"You chose: {services[num]}. What is your approximate budget?",
        }
        set_pending(chat_id, "open", "devis_budget")
        return messages.get(lang, messages["fr"])

    elif state == "devis_budget":
        flow["data"]["budget"] = user_text
        set_flow_state(chat_id, "devis_confirm", flow["data"])

        messages = {
            "fr": f"Récapitulatif :\n• Service : {flow['data'].get('service', 'N/A')}\n• Budget : {user_text}\n\nConfirmez-vous cette demande ? (Oui/Non)",
            "ar": f"ملخص:\n• الخدمة: {flow['data'].get('service', 'N/A')}\n• الميزانية: {user_text}\n\nهل تؤكد هذا الطلب؟ (نعم/لا)",
            "en": f"Summary:\n• Service: {flow['data'].get('service', 'N/A')}\n• Budget: {user_text}\n\nDo you confirm this request? (Yes/No)",
        }
        set_pending(chat_id, "confirmation", "devis_confirm")
        return messages.get(lang, messages["fr"])

    elif state == "devis_confirm":
        from pending_question import is_valid_answer
        is_valid, answer = is_valid_answer(chat_id, user_text)
        if not is_valid:
            return None

        if answer == "oui":
            clear_flow_state(chat_id)
            clear_pending(chat_id)
            messages = {
                "fr": "✅ Votre demande de devis a été enregistrée ! Nous vous contacterons dans les 24h.",
                "ar": "✅ تم تسجيل طلب عرض السعر الخاص بك! سنتواصل معك خلال 24 ساعة.",
                "en": "✅ Your quote request has been recorded! We will contact you within 24h.",
            }
            return messages.get(lang, messages["fr"])
        else:
            clear_flow_state(chat_id)
            clear_pending(chat_id)
            messages = {
                "fr": "Pas de problème. N'hésitez pas si vous changez d'avis !",
                "ar": "لا مشكلة. لا تتردد إذا غيرت رأيك!",
                "en": "No problem. Don't hesitate if you change your mind!",
            }
            return messages.get(lang, messages["fr"])

    return None
