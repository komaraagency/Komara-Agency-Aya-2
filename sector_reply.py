"""
Réponses sectorielles : détecte le domaine de la question et répond en priorité
avec les fiches correspondantes de la base de connaissances.
"""
import rag_engine

SECTOR_KEYWORDS = {
    "tarifs": {
        "fr": ["prix", "tarif", "coût", "cout", "combien", "budget", "devis", "euro", "€"],
        "ar": ["سعر", "تكلفة", "ميزانية", "عرض سعر", "كم", "يورو"],
        "en": ["price", "cost", "rate", "budget", "quote", "how much", "euro", "€"],
    },
    "services": {
        "fr": ["service", "prestation", "travail", "réalisation", "projet", "bot", "chatbot", "telegram", "whatsapp"],
        "ar": ["خدمة", "عمل", "مشروع", "تنفيذ", "بوت", "شات"],
        "en": ["service", "work", "project", "delivery", "bot", "chatbot", "telegram", "whatsapp"],
    },
    "delais": {
        "fr": ["délai", "temps", "durée", "quand", "combien de temps", "rapidement", "urgent"],
        "ar": ["موعد", "وقت", "مدة", "متى", "سريع", "عاجل"],
        "en": ["deadline", "time", "duration", "when", "how long", "quickly", "urgent"],
    },
    "contact": {
        "fr": ["contact", "téléphone", "email", "adresse", "joindre", "rdv", "rendez-vous", "appeler"],
        "ar": ["اتصال", "هاتف", "بريد", "عنوان", "موعد", "اتصل"],
        "en": ["contact", "phone", "email", "address", "appointment", "call"],
    },
    "automatisation": {
        "fr": ["automatisation", "automatique", "workflow", "intégration", "api", "flux"],
        "ar": ["أتمتة", "تلقائي", "تكامل", "api"],
        "en": ["automation", "automatic", "workflow", "integration", "api", "flow"],
    },
}


def detect_sector(text: str, lang: str) -> str | None:
    """Détecte le secteur/domaine de la question."""
    text_lower = text.lower()
    for sector, keywords_by_lang in SECTOR_KEYWORDS.items():
        keywords = keywords_by_lang.get(lang, keywords_by_lang.get("fr", []))
        for keyword in keywords:
            if keyword in text_lower:
                return sector
    return None


def get_sector_response(text: str, lang: str) -> str | None:
    """
    Tente de répondre en priorisant le secteur détecté.
    Retourne None si aucune réponse trouvée.
    """
    sector = detect_sector(text, lang)
    if sector is None:
        # Pas de secteur détecté, recherche RAG classique
        return rag_engine.get_best_answer(text, lang)

    # Recherche RAG avec le secteur en contexte
    enhanced_query = f"{sector} {text}"
    answer = rag_engine.get_best_answer(enhanced_query, lang)

    if answer is None:
        # Fallback : recherche sans le secteur
        answer = rag_engine.get_best_answer(text, lang)

    return answer
