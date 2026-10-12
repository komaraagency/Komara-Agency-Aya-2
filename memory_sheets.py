"""
Logging vers Google Sheets.
Tous les appels sont ASYNCHRONES pour ne pas bloquer le bot.
"""
import json
import logging
import threading
import time
import gspread

logger = logging.getLogger("komara.sheets")
from oauth2client.service_account import ServiceAccountCredentials
from config import GOOGLE_SHEETS_ID, GOOGLE_CREDENTIALS_JSON, GOOGLE_CREDENTIALS_PATH

# === Client Google Sheets ===
_gc = None
_sheet = None
_lock = threading.Lock()


def _load_credentials(scope):
    """Charge les identifiants : variable d'env en priorité (jamais
    dans le repo), sinon fichier credentials.json local."""
    if GOOGLE_CREDENTIALS_JSON.strip():
        data = json.loads(GOOGLE_CREDENTIALS_JSON)
        return ServiceAccountCredentials.from_json_keyfile_dict(data, scope)
    return ServiceAccountCredentials.from_json_keyfile_name(
        GOOGLE_CREDENTIALS_PATH, scope
    )


def _get_sheet():
    """Initialise le client Google Sheets (lazy loading)."""
    global _gc, _sheet
    if _sheet is None:
        with _lock:
            if _sheet is None:
                scope = [
                    "https://spreadsheets.google.com/feeds",
                    "https://www.googleapis.com/auth/drive",
                ]
                creds = _load_credentials(scope)
                _gc = gspread.authorize(creds)
                _sheet = _gc.open_by_key(GOOGLE_SHEETS_ID).sheet1
    return _sheet


def _write_to_sheet(chat_id: str, user_name: str, role: str, message: str, lang: str):
    """Écrit une ligne dans Google Sheets (appelé dans un thread séparé)."""
    try:
        sheet = _get_sheet()
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        sheet.append_row([timestamp, str(chat_id), user_name, role, message, lang])
    except Exception as e:
        # Boss 12/10 : erreur VISIBLE dans les logs Railway (fini le print muet)
        logger.error("[Sheets] Écriture impossible : %s", e)


def log_conversation(chat_id: str, user_name: str, role: str, message: str, lang: str = "fr"):
    """
    Log une conversation vers Google Sheets de manière ASYNCHRONE.
    Ne bloque jamais le thread principal.
    """
    thread = threading.Thread(
        target=_write_to_sheet,
        args=(chat_id, user_name, role, message, lang),
        daemon=True,
    )
    thread.start()


def get_last_messages(chat_id: str, n: int = 5) -> list[dict]:
    """Récupère les N derniers messages d'un chat (synchrone, pour le contexte RAG)."""
    try:
        sheet = _get_sheet()
        all_records = sheet.get_all_records()
        chat_records = [r for r in all_records if str(r.get("chat_id", "")) == str(chat_id)]
        return chat_records[-n:]
    except Exception as e:
        logger.error("[Sheets] Lecture impossible : %s", e)
        return []


def diagnose() -> str:
    """Boss 12/10 : état de la connexion Sheets en une ligne."""
    try:
        sheet = _get_sheet()
        return f"Sheets OK (onglet '{sheet.title}', {len(sheet.row_values(1))} colonnes)"
    except Exception as e:
        return f"Sheets ERREUR : {e}"
