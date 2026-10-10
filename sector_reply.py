"""
Réponses sectorielles : détecte le domaine de la question et répond en priorité
avec les fiches correspondantes de la base de connaissances.
"""
import rag_engine

SECTOR_KEYWORDS = {
    "tarifs": {
        "fr": ["prix", "tarif", "coût", "cout", "combien", "budget", "devis"],
        "ar": ["سعر", "تكلفة", "ميزانية", "عرض سعر", "كم"],
        "en": ["price", "cost", "rate", "budget", "quote", "how much"],
    },
    "services": {
        "fr": ["service", "prestation", "travail", "réalisation", "projet"],
        "ar": ["خدمة", "عمل", "مشروع", "تنفيذ"],
        "en": ["service", "work", "project", "delivery"],
    },
    "delais": {
        "fr": ["délai", "temps", "durée", "quand", "combien de temps"],
        "ar": ["موعد", "وقت", "مدة", "متى"],
        "en": ["deadline", "time", "duration", "when", "how long"],
    },
    "contact": {
        "fr": ["contact", "téléphone", "email", "adresse", "joindre", "rdv", "rendez-vous"],
        "ar": ["اتصال", "هاتف", "بريد", "عنوان", "موعد"],
        "en": ["contact", "phone", "email", "address", "appointment"],
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
