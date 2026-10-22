"""
Social Media Publishing Module for viz-reels
Publishes rendered vertical videos to Facebook Page (kreggscode) and Instagram (@kreggscode).
"""

import os
import sys
import json
from pathlib import Path

# Ensure UTF-8 output on Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))

try:
    from upload.upload_facebook import upload_to_facebook
    from upload.upload_instagram import upload_to_instagram
    from upload.upload_threads import upload_to_threads
except ImportError as e:
    print(f"⚠️ Import warning in publish.py: {e}")

def publish_video(video_path: Path, metadata: dict) -> dict:
    video_path = Path(video_path).resolve()
    if not video_path.exists():
        raise FileNotFoundError(f"Video file not found at: {video_path}")

    title = metadata.get("title", video_path.stem)
    raw_hashtags = metadata.get("hashtags", ["#systemdesign", "#backend", "#softwareengineering", "#coding", "#tech"])
    clean_tags = []
    if isinstance(raw_hashtags, list):
        for t in raw_hashtags:
            ct = str(t).strip().lower()
            if not ct.startswith("#"):
                ct = f"#{ct}"
            if ct not in clean_tags:
                clean_tags.append(ct)
    else:
        clean_tags = [t.lower() for t in str(raw_hashtags).split() if t.startswith("#")]
    clean_tags = clean_tags[:5]
    hashtags_str = " ".join(clean_tags)

    ig_caption = metadata.get("ig_caption", f"{title}")
    if clean_tags and clean_tags[0] not in ig_caption.lower():
        ig_caption = f"{ig_caption}\n\n.\n.\n{hashtags_str}"

    fb_caption = metadata.get("fb_caption", f"{title}")
    if clean_tags and clean_tags[0] not in fb_caption.lower():
        fb_caption = f"{fb_caption}\n\n{hashtags_str}"

    threads_caption = metadata.get("threads_caption", f"{title}\n\n{hashtags_str}")

    results = {}

    print(f"\n{'=' * 65}")
    print(f"🚀 PUBLISHING VIZ-REEL: {video_path.name}")
    print(f"📌 Title: {title}")
    print(f"{'=' * 65}")

    # 1. Instagram Reels (@kreggscode)
    try:
        print("\n📸 [Instagram] Publishing Reel to @kreggscode...")
        res_ig = upload_to_instagram(str(video_path), ig_caption)
        results["instagram"] = res_ig
        if res_ig.get("status") == "success":
            print(f"✅ [Instagram] Published successfully! Media ID: {res_ig.get('id')}")
        else:
            print(f"⚠️ [Instagram] Status: {res_ig}")
    except Exception as e:
        print(f"⚠️ [Instagram] Failed: {e}")
        results["instagram"] = {"status": "error", "error": str(e)}

    # 2. Facebook Reels (kreggscode Page)
    try:
        print("\n📘 [Facebook] Publishing Reel to kreggscode Page...")
        res_fb = upload_to_facebook(str(video_path), fb_caption, title=title[:100])
        results["facebook"] = res_fb
        if isinstance(res_fb, dict) and res_fb.get("status") == "success":
            print(f"✅ [Facebook] Published successfully! Video ID: {res_fb.get('id')}")
        else:
            print(f"ℹ️ [Facebook] Response: {res_fb}")
    except Exception as e:
        print(f"⚠️ [Facebook] Failed: {e}")
        results["facebook"] = {"status": "error", "error": str(e)}

    # 3. Threads
    try:
        print("\n🧵 [Threads] Publishing Post...")
        res_threads = upload_to_threads(str(video_path), threads_caption)
        results["threads"] = res_threads
    except Exception as e:
        print(f"⚠️ [Threads] Note: {e}")
        results["threads"] = {"status": "skipped", "reason": str(e)}

    print(f"\n{'=' * 65}")
    print("🏁 Publishing cycle finished.")
    print(f"{'=' * 65}\n")
    return results

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python publish.py <video_path> [metadata_json_path]")
        sys.exit(1)

    vpath = Path(sys.argv[1])
    mdata = {}
    if len(sys.argv) > 2 and Path(sys.argv[2]).exists():
        with open(sys.argv[2], "r", encoding="utf-8") as f:
            mdata = json.load(f)

    publish_video(vpath, mdata)
