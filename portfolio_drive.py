"""
Portfolio Google Drive : liste les visuels du dossier portfolio.
Retourne une liste numérotée (titre + lien) ; le client choisit par
numéro ou titre — jamais d'envoi au hasard.
"""
import threading
from config import GOOGLE_CREDENTIALS_PATH, GOOGLE_DRIVE_FOLDER_ID

_service = None
_lock = threading.Lock()
_cache = None  # [(title, url)]


def _get_service():
    global _service
    if _service is None:
        with _lock:
            if _service is None:
                from googleapiclient.discovery import build
                from googleapiclient.http import MediaIoBaseDownload  # noqa: F401
                from oauth2client.service_account import ServiceAccountCredentials
                scope = ["https://www.googleapis.com/auth/drive.readonly"]
                creds = ServiceAccountCredentials.from_json_keyfile_name(
                    GOOGLE_CREDENTIALS_PATH, scope)
                _service = build("drive", "v3", credentials=creds,
                                 cache_discovery=False)
    return _service


def get_gallery() -> list[tuple[str, str]]:
    """Liste les fichiers du dossier portfolio. Retourne [(titre, lien)]."""
    global _cache
    if _cache is not None:
        return _cache
    try:
        service = _get_service()
        resp = service.files().list(
            q=f"'{GOOGLE_DRIVE_FOLDER_ID}' in parents and trashed = false",
            fields="files(id, name, webViewLink)",
            pageSize=50,
            orderBy="name desc",
        ).execute()
        files = [
            (f["name"], f.get("webViewLink", ""))
            for f in resp.get("files", [])
        ]
        _cache = files
        return files
    except Exception as e:
        print(f"[Drive] Erreur portfolio: {e}")
        return []


def reset_cache():
    """Force le rechargement de la galerie (après ajout d'un visuel)."""
    global _cache
    with _lock:
        _cache = None


def numbered_list(lang: str) -> str | None:
    """Rendu numéroté de la galerie, multilingue."""
    files = get_gallery()
    if not files:
        return None
    headers = {
        "fr": " Nos réalisations — choisissez un numéro ou un titre 👇",
        "ar": " أعمالنا — اختر رقما أو عنوانا 👇",
        "en": " Our work — pick a number or a title 👇",
    }
    lines = [headers.get(lang, headers["fr"])]
    for i, (title, _url) in enumerate(files, 1):
        lines.append(f"{i}\ufe0f\u20e3 {title}")
    return "\n".join(lines)


def pick(selection: str) -> tuple[str, str] | None:
    """Retourne (titre, lien) pour un numéro ou un titre choisi, sinon None."""
    files = get_gallery()
    selection = selection.strip()
    if selection.isdigit():
        idx = int(selection)
        if 1 <= idx <= len(files):
            return files[idx - 1]
        return None
    low = selection.lower()
    for title, url in files:
        if low in title.lower():
            return title, url
    return None
