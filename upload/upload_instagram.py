"""
Instagram Reels Upload for kreggscode
Uploads Reels to Instagram Professional Account (@kreggscode: 17841452339411557).
Uses official Meta Graph API Resumable Upload Protocol (direct byte streaming to rupload.facebook.com).
"""

import os
import sys
import time
import requests
import subprocess
import tempfile
from pathlib import Path
from dotenv import load_dotenv

# Ensure UTF-8 output on Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

env_path = Path(__file__).resolve().parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

DEFAULT_IG_USER_ID = "17841452339411557"
ACCOUNT_NAME = "kreggscode"

def get_instagram_credentials():
    """
    Retrieves Instagram Account ID and Access Token from environment.
    """
    user_id = (
        os.getenv('INSTAGRAM_ACCOUNT_ID') or 
        os.getenv('IG_USER_ID') or 
        DEFAULT_IG_USER_ID
    )
    access_token = (
        os.getenv('INSTAGRAM_ACCESS_TOKEN') or 
        os.getenv('FACEBOOK_PAGE_ACCESS_TOKEN') or 
        os.getenv('FACEBOOK_ACCESS_TOKEN')
    )
    return user_id, access_token

def upload_via_public_url(video_path: Path, user_id: str, access_token: str, caption: str) -> dict:
    """
    Fallback method: Uploads video to tmpfiles.org and creates container using video_url.
    """
    print("[instagram] 🌐 Attempting fallback upload via tmpfiles.org...")
    with open(video_path, 'rb') as f:
        res = requests.post(
            'https://tmpfiles.org/api/v1/upload',
            files={'file': (video_path.name, f, 'video/mp4')},
            timeout=180
        )
    if res.status_code != 200:
        raise Exception(f"tmpfiles upload failed: {res.text}")

    data = res.json()
    raw_url = data.get('data', {}).get('url', '')
    if not raw_url:
        raise Exception("tmpfiles returned no URL")

    # Convert to direct download URL
    video_url = raw_url.replace('tmpfiles.org/', 'tmpfiles.org/dl/').replace('http://', 'https://')
    print(f"[instagram] Direct download URL ready: {video_url}")

    container_url = f"https://graph.facebook.com/v21.0/{user_id}/media"
    container_params = {
        'media_type': 'REELS',
        'video_url': video_url,
        'caption': caption[:2200],
        'share_to_feed': 'false',
        'access_token': access_token
    }
    c_res = requests.post(container_url, data=container_params, timeout=60)
    if c_res.status_code != 200:
        raise Exception(f"Container creation failed with URL: {c_res.text}")

    container_id = c_res.json().get('id')
    return wait_and_publish_container(container_id, user_id, access_token)

def wait_and_publish_container(container_id: str, user_id: str, access_token: str) -> dict:
    """
    Polls container processing status until FINISHED, then publishes the Reel.
    """
    print(f"[instagram] ⏳ Waiting for container {container_id} to finish processing...")
    status_url = f"https://graph.facebook.com/v21.0/{container_id}"
    status_params = {
        "fields": "status_code,status",
        "access_token": access_token
    }

    max_retries = 36  # ~3 minutes max
    for attempt in range(max_retries):
        time.sleep(5)
        try:
            stat_res = requests.get(status_url, params=status_params, timeout=30)
            if stat_res.status_code == 200:
                stat_json = stat_res.json()
                status_code = stat_json.get("status_code")
                print(f"[instagram] Status check ({attempt + 1}/{max_retries}): {status_code}")
                if status_code == "FINISHED":
                    break
                if status_code == "ERROR":
                    raise Exception(f"Container processing error: {stat_json}")
        except Exception as e:
            if "Container processing error" in str(e):
                raise
            print(f"[instagram] Status query notice: {e}")

    # Publish
    print("[instagram] 🚀 Step 3: Publishing Reel to Reels tab only (main grid excluded)...")
    publish_url = f"https://graph.facebook.com/v21.0/{user_id}/media_publish"
    publish_data = {
        "creation_id": container_id,
        "access_token": access_token
    }
    pub_res = requests.post(publish_url, data=publish_data, timeout=60)

    if pub_res.status_code != 200:
        # Retry once after 15s if Meta is still syncing
        time.sleep(15)
        pub_res = requests.post(publish_url, data=publish_data, timeout=60)

    if pub_res.status_code == 200:
        media_id = pub_res.json().get("id")
        print(f"[instagram] ✅ SUCCESS! Reel published to @{ACCOUNT_NAME}! Media ID: {media_id}")
        print("=" * 60)
        return {'id': media_id, 'platform': 'instagram', 'status': 'success'}
    else:
        err_msg = pub_res.json() if pub_res.text else pub_res.text
        raise Exception(f"Media publish failed: {err_msg}")

def upload_to_instagram(video_path, caption, is_story=False):
    """
    Uploads vertical video to Instagram (@kreggscode) as a Reel.
    """
    print("\n" + "=" * 60)
    print(f"📸 INSTAGRAM REEL UPLOAD (@{ACCOUNT_NAME}) STARTING")
    print("=" * 60)

    video_path_obj = Path(video_path).resolve()
    if not video_path_obj.exists():
        error_msg = f"❌ Video file not found: {video_path}"
        print(f"[instagram] {error_msg}")
        raise FileNotFoundError(error_msg)

    user_id, access_token = get_instagram_credentials()

    if not access_token:
        print("[instagram] ⚠️ Skipping Instagram upload: INSTAGRAM_ACCESS_TOKEN not set.")
        return {'status': 'skipped', 'reason': 'Missing access token', 'platform': 'instagram'}

    def mask(s):
        return f"{s[:8]}...{s[-4:]}" if s and len(s) > 12 else "SET"

    file_size = video_path_obj.stat().st_size
    file_size_mb = file_size / (1024 * 1024)
    caption_limited = caption[:2200] if len(caption) > 2200 else caption

    print(f"[instagram] Target Account: @{ACCOUNT_NAME} (ID: {user_id})")
    print(f"[instagram] Token: {mask(access_token)}")
    print(f"[instagram] Video: {video_path_obj.name} ({file_size_mb:.2f} MB)")
    print(f"[instagram] Caption Length: {len(caption_limited)} characters")

    # Primary Method: Direct Meta Resumable Upload
    try:
        print("\n[instagram] 🎬 Step 1: Initializing resumable Reel container...")
        init_url = f"https://graph.facebook.com/v21.0/{user_id}/media"
        init_data = {
            'upload_type': 'resumable',
            'media_type': 'REELS',
            'caption': caption_limited,
            'share_to_feed': 'false',
            'access_token': access_token
        }
        init_res = requests.post(init_url, data=init_data, timeout=60)

        if init_res.status_code == 200:
            res_json = init_res.json()
            container_id = res_json.get('id')
            upload_url = res_json.get('uri')
            print(f"[instagram] ✅ Container created: {container_id}")

            print("[instagram] 📤 Step 2: Uploading video bytes to rupload...")
            rupload_headers = {
                'Authorization': f'OAuth {access_token}',
                'offset': '0',
                'file_size': str(file_size),
                'Content-Type': 'application/octet-stream'
            }
            with open(video_path_obj, 'rb') as f:
                up_res = requests.post(upload_url, headers=rupload_headers, data=f, timeout=300)

            if up_res.status_code in (200, 204) or up_res.json().get('success'):
                print(f"[instagram] ✅ Video bytes streamed successfully!")
            else:
                print(f"[instagram] ⚠️ Byte upload note: {up_res.status_code} {up_res.text}")

            result = wait_and_publish_container(container_id, user_id, access_token)
            return result
        else:
            print(f"[instagram] ⚠️ Resumable init failed ({init_res.status_code}): {init_res.text}")
            print("[instagram] Switching to fallback public URL upload method...")
            return upload_via_public_url(video_path_obj, user_id, access_token, caption_limited)

    except Exception as e:
        print(f"[instagram] ⚠️ Resumable upload error: {e}")
        try:
            return upload_via_public_url(video_path_obj, user_id, access_token, caption_limited)
        except Exception as fe:
            print(f"[instagram] ❌ Fallback upload also failed: {fe}")
            return {'status': 'failed', 'platform': 'instagram', 'error': str(e)}

if __name__ == '__main__':
    if len(sys.argv) > 1:
        v_file = Path(sys.argv[1])
        if v_file.exists():
            res = upload_to_instagram(str(v_file), "Automated Tech Reel #coding #tech")
            print("Result:", res)
        else:
            print("File not found:", v_file)
    else:
        print("Usage: python upload_instagram.py <video_path>")
