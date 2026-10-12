"""
Configuration centralisée du bot.
Charge les variables d'environnement et définit les constantes.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# === Telegram ===
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "0"))

# === Google ===
GOOGLE_SHEETS_ID = os.getenv("GOOGLE_SHEETS_ID", "")
GOOGLE_DRIVE_FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID", "")
GOOGLE_CREDENTIALS_PATH = os.getenv("GOOGLE_CREDENTIALS_PATH", "./credentials.json")

# Compte de service en variable d'env (recommandé sur Railway : jamais
# de fichier credentials.json dans le repo). Contenu JSON complet.
GOOGLE_CREDENTIALS_JSON = os.getenv("GOOGLE_CREDENTIALS_JSON", "")

# === Langue ===
DEFAULT_LANGUAGE = os.getenv("DEFAULT_LANGUAGE", "fr")
SUPPORTED_LANGUAGES = ["fr", "ar", "en"]

# === RAG ===
EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"  # Gratuit, local, multilingue
RAG_TOP_K = 3
RAG_MIN_SCORE = 0.65
KNOWLEDGE_BASE_PATH = "./knowledge_base"

# === Performance ===
MAX_CACHE_SIZE = 10000
CACHE_TTL_SECONDS = 86400  # 24h
SHEETS_LOG_ASYNC = True  # Logging asynchrone

# === Chemins ===
MEMORY_DIR = os.getenv("MEMORY_DIR", "/tmp/komara_memory")
SQLITE_DB_PATH = os.path.join(MEMORY_DIR, "memory.db")
