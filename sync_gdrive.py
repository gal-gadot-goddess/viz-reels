"""
Google Drive Sync for viz-reels
Syncs HTML animations (with Web Audio SFX) and background music from Google Drive using Service Account.
"""

import os
import sys
import json
import io
from pathlib import Path
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from dotenv import load_dotenv

# Ensure UTF-8 output on Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

env_path = Path(__file__).resolve().parent / '.env'
load_dotenv(dotenv_path=env_path)

BASE_DIR = Path(__file__).resolve().parent
HTML_DIR = BASE_DIR / "html_sources"
MUSIC_DIR = BASE_DIR / "music"

# Default Google Drive Folder IDs
DEFAULT_HTML_FOLDER = "1OnHqUxj0B9TEBuu1Qq0RTHqoqgXbvr_G"
DEFAULT_MUSIC_FOLDER = "19zTCpkmKpZwUm8j8gnvfHZqVJqfwEz9I"

def get_drive_service():
    sa_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_KEY")
    if not sa_json:
        return None
    try:
        sa_info = json.loads(sa_json)
        creds = service_account.Credentials.from_service_account_info(
            sa_info,
            scopes=['https://www.googleapis.com/auth/drive.readonly']
        )
        return build('drive', 'v3', credentials=creds)
    except Exception as e:
        print(f"⚠️ Error creating Google Drive service: {e}")
        return None

def download_folder_files(service, folder_id: str, target_dir: Path, valid_exts: list = None) -> list:
    target_dir.mkdir(parents=True, exist_ok=True)
    downloaded = []
    
    print(f"\n📂 Syncing Folder (ID: {folder_id}) -> {target_dir.name}/")
    query = f"'{folder_id}' in parents and trashed = false"
    
    page_token = None
    all_files = []
    while True:
        results = service.files().list(
            q=query,
            pageSize=100,
            fields="nextPageToken, files(id, name, mimeType, size)",
            pageToken=page_token
        ).execute()
        all_files.extend(results.get('files', []))
        page_token = results.get('nextPageToken')
        if not page_token:
            break
            
    print(f"Found {len(all_files)} file(s) in Drive folder.")

    for f in all_files:
        name = f['name']
        file_id = f['id']
        ext = Path(name).suffix.lower()
        if valid_exts and ext not in valid_exts:
            continue
            
        dest = target_dir / name
        # Skip if already exists and size matches
        if dest.exists() and f.get('size') and dest.stat().st_size == int(f['size']):
            downloaded.append(name)
            continue
            
        print(f"  ⬇️  Downloading: {name} ({f.get('size', 'unknown')} bytes)")
        request = service.files().get_media(fileId=file_id)
        fh = io.FileIO(dest, 'wb')
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
        fh.close()
        downloaded.append(name)

    return downloaded

def sync_all():
    service = get_drive_service()
    if not service:
        print("ℹ️ GOOGLE_SERVICE_ACCOUNT_KEY not configured. Skipping Drive sync.")
        return

    html_folder = os.environ.get("GDRIVE_HTML_FOLDER_ID", DEFAULT_HTML_FOLDER)
    music_folder = os.environ.get("GDRIVE_MUSIC_FOLDER_ID", DEFAULT_MUSIC_FOLDER)

    html_files = download_folder_files(service, html_folder, HTML_DIR, valid_exts=['.html', '.htm'])
    music_files = download_folder_files(service, music_folder, MUSIC_DIR, valid_exts=['.mp3', '.wav', '.m4a'])

    print("\n✅ Sync complete!")
    print(f"  HTML files synced: {len(html_files)}")
    print(f"  Music tracks synced: {len(music_files)}\n")

if __name__ == "__main__":
    sync_all()
