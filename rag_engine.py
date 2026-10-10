"""
Moteur RAG (Retrieval-Augmented Generation) 100% local et gratuit.
Utilise sentence-transformers pour les embeddings et SQLite + numpy pour le search.
"""
import os
import numpy as np
import threading
from config import (
    EMBEDDING_MODEL, RAG_TOP_K, RAG_MIN_SCORE,
    KNOWLEDGE_BASE_PATH, SUPPORTED_LANGUAGES,
)

# === Modèle d'embedding (chargé une seule fois) ===
_model = None
_model_lock = threading.Lock()


def _get_model():
    """Charge le modèle d'embedding (lazy loading, thread-safe)."""
    global _model
    if _model is None:
        with _model_lock:
            if _model is None:
                from sentence_transformers import SentenceTransformer
                _model = SentenceTransformer(EMBEDDING_MODEL)
    return _model


# === Base de connaissances en mémoire ===
_kb_cache = {}  # {lang: [{"text": ..., "embedding": [...], "source": ...}]}
_kb_lock = threading.Lock()


def _load_knowledge_base():
    """Charge tous les fichiers de la base de connaissances en mémoire."""
    global _kb_cache
    model = _get_model()

    with _kb_lock:
        for lang in SUPPORTED_LANGUAGES:
            lang_dir = os.path.join(KNOWLEDGE_BASE_PATH, lang)
            if not os.path.exists(lang_dir):
                continue

            entries = []
            for filename in sorted(os.listdir(lang_dir)):
                if not filename.endswith(".md"):
                    continue

                filepath = os.path.join(lang_dir, filename)
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()

                # Découper par sections (titres ##)
                sections = _split_into_sections(content, filename)
                for section in sections:
                    if len(section["text"].strip()) < 20:
                        continue  # Ignorer les sections trop courtes

                    embedding = model.encode(section["text"]).tolist()
                    entries.append({
                        "text": section["text"],
                        "embedding": embedding,
                        "source": section["source"],
                        "lang": lang,
                    })

            _kb_cache[lang] = entries

    print(f"[RAG] Base de connaissances chargée: {sum(len(v) for v in _kb_cache.values())} sections")


def _split_into_sections(content: str, filename: str) -> list[dict]:
    """Découpe un fichier markdown en sections basées sur les titres."""
    sections = []
    current_title = filename.replace(".md", "")
    current_text = ""

    for line in content.split("\n"):
        if line.startswith("## "):
            if current_text.strip():
                sections.append({
                    "text": f"{current_title}\n{current_text.strip()}",
                    "source": f"{filename}#{current_title}",
                })
            current_title = line[3:].strip()
            current_text = ""
        elif line.startswith("# "):
            if current_text.strip():
                sections.append({
                    "text": f"{current_title}\n{current_text.strip()}",
                    "source": f"{filename}#{current_title}",
                })
            current_title = line[2:].strip()
            current_text = ""
        else:
            current_text += line + "\n"

    # Dernière section
    if current_text.strip():
        sections.append({
            "text": f"{current_title}\n{current_text.strip()}",
            "source": f"{filename}#{current_title}",
        })

    return sections


def _cosine_similarity(a: list, b: list) -> float:
    """Calcule la similarité cosinus entre deux vecteurs."""
    a_np = np.array(a)
    b_np = np.array(b)
    dot = np.dot(a_np, b_np)
    norm_a = np.linalg.norm(a_np)
    norm_b = np.linalg.norm(b_np)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(dot / (norm_a * norm_b))


def search(query: str, lang: str, top_k: int = RAG_TOP_K, min_score: float = RAG_MIN_SCORE) -> list[dict]:
    """
    Recherche les sections les plus pertinentes pour une requête.

    IMPORTANT: Ne cherche QUE dans la langue demandée.
    Pas de fallback vers une autre langue (anti-mélange).
    """
    if not _kb_cache:
        _load_knowledge_base()

    model = _get_model()
    query_embedding = model.encode(query).tolist()

    # Chercher UNIQUEMENT dans la langue du client
    entries = _kb_cache.get(lang, [])
    if not entries:
        return []  # Pas de fallback vers FR ! (Correction critique)

    results = []
    for entry in entries:
        score = _cosine_similarity(query_embedding, entry["embedding"])
        if score >= min_score:
            results.append({
                "text": entry["text"],
                "source": entry["source"],
                "score": score,
            })

    # Trier par score décroissant
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:top_k]


def get_best_answer(query: str, lang: str) -> str | None:
    """
    Retourne la meilleure réponse RAG pour une requête dans une langue donnée.
    Retourne None si aucune réponse trouvée (pas de fallback multilingue).
    """
    results = search(query, lang)
    if not results:
        return None

    # Combiner les meilleurs résultats
    best = results[0]
    return best["text"]


def get_context_for_generation(query: str, lang: str) -> str:
    """Retourne le contexte formaté pour la génération de réponse."""
    results = search(query, lang)
    if not results:
        return ""

    context_parts = []
    for i, r in enumerate(results, 1):
        context_parts.append(f"[Source {i} - {r['source']} (score: {r['score']:.2f})]\n{r['text']}")

    return "\n\n---\n\n".join(context_parts)


def reload_knowledge_base():
    """Recharge la base de connaissances (utile après mise à jour des fichiers)."""
    global _kb_cache
    with _kb_lock:
        _kb_cache = {}
    _load_knowledge_base()
