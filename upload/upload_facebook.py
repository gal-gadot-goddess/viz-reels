"""
Facebook Reels & Story Upload for kreggscode
Uploads vertical video Reels and Stories to Facebook Page (kreggscode: 503243842882427).
Uses official Facebook Video Reels Resumable API.
"""

import os
import sys
import time
import requests
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

# Default to kreggscode Facebook Page ID
DEFAULT_PAGE_ID = "503243842882427"
PAGE_NAME = "kreggscode"

def get_page_credentials():
    """
    Retrieves Facebook Page ID and Page Access Token from environment.
    """
    page_id = (
        os.getenv('FACEBOOK_PAGE_ID') or 
        os.getenv('FB_PAGE_ID') or 
        DEFAULT_PAGE_ID
    )
    access_token = (
        os.getenv('FACEBOOK_PAGE_ACCESS_TOKEN') or 
        os.getenv('FACEBOOK_ACCESS_TOKEN') or 
        os.getenv('FB_PAGE_ACCESS_TOKEN') or 
        os.getenv('FB_ACCESS_TOKEN')
    )
    return page_id, access_token

def upload_to_facebook(video_path, description, title="Tech Short", thumbnail_path=None, thumb_path=None):
    """
    Uploads vertical video to Facebook Page as a Reel.
    """
    active_thumb = thumbnail_path or thumb_path
    if not active_thumb:
        cand = Path(video_path).with_suffix(".jpg")
        if cand.exists():
            active_thumb = cand

    print("\n" + "=" * 60)
    print(f"📘 FACEBOOK REEL UPLOAD ({PAGE_NAME}) STARTING")
    print("=" * 60)

    video_path_obj = Path(video_path).resolve()
    if not video_path_obj.exists():
        error_msg = f"❌ Video file not found: {video_path}"
        print(f"[facebook] {error_msg}")
        raise FileNotFoundError(error_msg)

    page_id, access_token = get_page_credentials()

    if not access_token:
        print("[facebook] ⚠️ Skipping Facebook upload: FACEBOOK_PAGE_ACCESS_TOKEN not set.")
        return {'status': 'skipped', 'reason': 'Missing access token', 'platform': 'facebook'}

    def mask(s):
        return f"{s[:8]}...{s[-4:]}" if s and len(s) > 12 else "SET"

    file_size = video_path_obj.stat().st_size
    file_size_mb = file_size / (1024 * 1024)
    print(f"[facebook] Target Page: '{PAGE_NAME}' (ID: {page_id})")
    print(f"[facebook] Token: {mask(access_token)}")
    print(f"[facebook] Video: {video_path_obj.name} ({file_size_mb:.2f} MB)")

    # Method 1: Meta Video Reels API (official for Reels)
    try:
        print("\n[facebook] 🎬 Step 1: Initializing Reel upload session...")
        init_url = f"https://graph.facebook.com/v21.0/{page_id}/video_reels"
        init_res = requests.post(
            init_url,
            data={
                'upload_phase': 'start',
                'access_token': access_token
            },
            timeout=30
        )

        if init_res.status_code == 200:
            init_data = init_res.json()
            video_id = init_data.get('video_id')
            upload_url = init_data.get('upload_url')
            print(f"[facebook] ✅ Reel session created! Video ID: {video_id}")

            print(f"[facebook] 📤 Step 2: Uploading video bytes to rupload...")
            rupload_headers = {
                'Authorization': f'OAuth {access_token}',
                'offset': '0',
                'file_size': str(file_size),
                'Content-Type': 'application/octet-stream'
            }
            with open(video_path_obj, 'rb') as vf:
                up_res = requests.post(upload_url, headers=rupload_headers, data=vf, timeout=300)

            if up_res.status_code in (200, 204) or up_res.json().get('success'):
                print(f"[facebook] ✅ Video bytes uploaded successfully!")
            else:
                print(f"[facebook] ⚠️ Upload note: {up_res.status_code} {up_res.text}")

            print(f"[facebook] 🚀 Step 3: Publishing Reel...")
            finish_data = {
                'upload_phase': 'finish',
                'access_token': access_token,
                'video_id': video_id,
                'video_state': 'PUBLISHED',
                'description': description,
                'title': title[:100]
            }
            fin_res = requests.post(init_url, data=finish_data, timeout=60)
            fin_json = fin_res.json()

            if fin_res.status_code == 200 and fin_json.get('success'):
                print(f"[facebook] ✅ SUCCESS! Reel published to '{PAGE_NAME}'! Video ID: {video_id}")

                # Attach preferred custom cover thumbnail
                if active_thumb and Path(active_thumb).exists():
                    try:
                        print(f"[facebook] 🖼️ Setting preferred custom cover: {Path(active_thumb).name}...")
                        thumb_edge_url = f"https://graph.facebook.com/v21.0/{video_id}/thumbnails"
                        with open(active_thumb, 'rb') as tf:
                            t_res = requests.post(
                                thumb_edge_url,
                                data={'access_token': access_token, 'is_preferred': 'true'},
                                files={'source': tf},
                                timeout=30
                            )
                        if t_res.status_code == 200:
                            print(f"[facebook] ✅ Custom cover thumbnail set successfully!")
                        else:
                            print(f"[facebook] ⚠️ Custom thumbnail response: {t_res.status_code} {t_res.text}")
                    except Exception as te:
                        print(f"[facebook] ⚠️ Custom thumbnail attachment error: {te}")

                print("=" * 60)
                return {'id': video_id, 'page': PAGE_NAME, 'status': 'success'}
            else:
                print(f"[facebook] ⚠️ Reel finish response: {fin_json}. Falling back to standard video API...")
        else:
            print(f"[facebook] ⚠️ video_reels start failed: {init_res.text}. Falling back to standard video API...")

    except Exception as e:
        print(f"[facebook] ⚠️ video_reels error: {e}. Falling back to standard video API...")

    # Method 2: Standard Page Videos API fallback
    try:
        print("\n[facebook] 🔄 Falling back to /{page_id}/videos endpoint...")
        url = f"https://graph.facebook.com/v21.0/{page_id}/videos"
        with open(video_path_obj, 'rb') as video_file:
            files = {'file': video_file}
            thumb_file = None
            if active_thumb and Path(active_thumb).exists():
                thumb_file = open(active_thumb, 'rb')
                files['thumb'] = thumb_file

            data = {
                'access_token': access_token,
                'description': description,
                'title': title[:100],
                'is_explicit_share': True,
                'is_reel': True
            }

            resp = requests.post(url, files=files, data=data, timeout=300)
            if thumb_file:
                thumb_file.close()

            if resp.status_code == 200:
                result = resp.json()
                video_id = result.get('id')
                print(f"[facebook] ✅ SUCCESS on '{PAGE_NAME}'! Video ID: {video_id}")
                print("=" * 60)
                return {'id': video_id, 'page': PAGE_NAME, 'status': 'success'}
            else:
                err = resp.json() if resp.text else {}
                err_msg = err.get('error', {}).get('message', resp.text)
                print(f"[facebook] ❌ Failed on '{PAGE_NAME}': {err_msg}")
                print("=" * 60)
                return {'status': 'failed', 'page': PAGE_NAME, 'error': err_msg}

    except Exception as e:
        print(f"[facebook] ❌ Facebook upload exception: {e}")
        print("=" * 60)
        return {'status': 'failed', 'page': PAGE_NAME, 'error': str(e)}

def upload_to_facebook_story(video_path):
    """
    Uploads vertical video to Facebook Page as a Story.
    """
    print("\n" + "=" * 60)
    print(f"📘 FACEBOOK STORY UPLOAD ({PAGE_NAME}) STARTING")
    print("=" * 60)

    video_path_obj = Path(video_path).resolve()
    if not video_path_obj.exists():
        raise FileNotFoundError(f"[facebook] Video not found: {video_path}")

    page_id, access_token = get_page_credentials()
    if not access_token:
        print("[facebook] Skipping Story upload - access token not set")
        return {'status': 'skipped', 'reason': 'Missing credentials'}

    file_size = video_path_obj.stat().st_size

    try:
        init_url = f"https://graph.facebook.com/v21.0/{page_id}/video_stories"
        init_data = {
            'access_token': access_token,
            'upload_phase': 'start',
            'file_size': file_size
        }
        res_init = requests.post(init_url, data=init_data, timeout=30)
        if res_init.status_code != 200:
            print(f"[facebook] ❌ Story Init Error: {res_init.text}")
            return {'status': 'failed', 'error': res_init.text}

        init_json = res_init.json()
        upload_url = init_json.get('upload_url')
        video_id = init_json.get('video_id')

        headers = {
            'Authorization': f'OAuth {access_token}',
            'offset': '0',
            'file_size': str(file_size),
            'Content-Type': 'application/octet-stream'
        }
        with open(video_path_obj, 'rb') as f:
            requests.post(upload_url, data=f, headers=headers, timeout=300)

        finish_data = {
            'access_token': access_token,
            'upload_phase': 'finish',
            'video_id': video_id
        }
        res_finish = requests.post(init_url, data=finish_data, timeout=60)

        if res_finish.status_code == 200 or res_finish.json().get('success'):
            print(f"[facebook] ✅ SUCCESS Story on '{PAGE_NAME}'! Video ID: {video_id}")
            print("=" * 60)
            return {'id': video_id, 'page': PAGE_NAME, 'status': 'success'}
        else:
            print(f"[facebook] ❌ Finish Story Error: {res_finish.text}")
            print("=" * 60)
            return {'status': 'failed', 'error': res_finish.text}

    except Exception as e:
        print(f"[facebook] ❌ Story failed: {e}")
        print("=" * 60)
        return {'status': 'failed', 'error': str(e)}

if __name__ == '__main__':
    if len(sys.argv) > 1:
        v_file = Path(sys.argv[1])
        if v_file.exists():
            res = upload_to_facebook(str(v_file), "Automated Tech Short #coding #tech")
            print("Result:", res)
        else:
            print("File not found:", v_file)
    else:
        print("Usage: python upload_facebook.py <video_path>")
