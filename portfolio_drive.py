"""
Gestion du portfolio via Google Drive.
Télécharge les images et les envoie via Telegram.
"""
import json
import os
import io
import threading
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from oauth2client.service_account import ServiceAccountCredentials
from config import GOOGLE_DRIVE_FOLDER_ID, GOOGLE_CREDENTIALS_JSON, GOOGLE_CREDENTIALS_PATH

_drive_service = None
_lock = threading.Lock()


def _get_drive_service():
    """Initialise le service Google Drive (lazy loading)."""
    global _drive_service
    if _drive_service is None:
        with _lock:
            if _drive_service is None:
                scope = ["https://www.googleapis.com/auth/drive.readonly"]
                if GOOGLE_CREDENTIALS_JSON.strip():
                    data = json.loads(GOOGLE_CREDENTIALS_JSON)
                    creds = ServiceAccountCredentials.from_json_keyfile_dict(
                        data, scope)
                else:
                    creds = ServiceAccountCredentials.from_json_keyfile_name(
                        GOOGLE_CREDENTIALS_PATH, scope
                    )
                _drive_service = build("drive", "v3", credentials=creds)
    return _drive_service


def list_portfolio_images() -> list[dict]:
    """Liste toutes les images du dossier portfolio."""
    try:
        service = _get_drive_service()
        query = f"'{GOOGLE_DRIVE_FOLDER_ID}' in parents and mimeType contains 'image/'"
        results = service.files().list(
            q=query,
            fields="files(id, name, mimeType)",
            pageSize=50,
        ).execute()

        files = results.get("files", [])
        return [{"id": f["id"], "name": f["name"]} for f in files]
    except Exception as e:
        print(f"[Drive] Erreur listing: {e}")
        return []


def download_image(file_id: str) -> bytes | None:
    """Télécharge une image depuis Drive."""
    try:
        service = _get_drive_service()
        request = service.files().get_media(fileId=file_id)

        # Téléchargement par chunks pour éviter OOM
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()

        fh.seek(0)
        return fh.read()
    except Exception as e:
        print(f"[Drive] Erreur téléchargement: {e}")
        return None


def get_image_url(file_id: str) -> str | None:
    """
    Retourne l'URL publique d'une image (si partagée).
    Plus rapide que le téléchargement direct.
    """
    try:
        return f"https://drive.google.com/uc?export=view&id={file_id}"
    except Exception:
        return None
