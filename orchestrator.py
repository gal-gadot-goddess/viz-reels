"""
Automated Pipeline Orchestrator for viz-reels
Coordinates: Google Drive Sync -> Weighted LRU Selection -> Web Audio SFX Video Render -> AI Metadata -> Social Media Upload
Follows the canonical once-daily weighted-average/LRU publishing law.
"""

import os
import sys
import json
import time
import random
import argparse
from pathlib import Path

# Ensure UTF-8 output on Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent
HTML_DIR = BASE_DIR / "html_sources"
MUSIC_DIR = BASE_DIR / "music"
OUTPUT_DIR = BASE_DIR / "output"
HISTORY_FILE = BASE_DIR / "history.json"
METADATA_FILE = BASE_DIR / "metadata.json"

from sync_gdrive import sync_all
from converter import convert_html_to_video
from generate_metadata import clean_filename_to_title, generate_ai_metadata
from publish import publish_video

def load_history() -> list:
    if HISTORY_FILE.exists():
        try:
            return json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []

def save_history(history: list):
    HISTORY_FILE.write_text(json.dumps(history, indent=2, ensure_ascii=False), encoding="utf-8")

def select_candidate_weighted_lru(candidates: list, history: list, allow_recirculation: bool = True):
    """
    Selects candidate following the canonical Weighted Least-Recently-Used (LRU) / Weighted Average law:
    1. Strict priority to completely unpublished items (count == 0).
    2. Once all items are published (Recirculation Mode):
       Calculates usage frequency for each candidate from history.
       Computes inverse exponential weights: weight = max(1, 1000 // (3 ** min(count, 6))).
       Performs a weighted random selection, ensuring least-used items have exponentially higher probability.
    """
    if not candidates:
        return None

    counts = {}
    for entry in history:
        name = entry.get("file", "").strip().lower()
        if name:
            counts[name] = counts.get(name, 0) + 1

    # 1. Unpublished items
    unpublished = [c for c in candidates if c.name.strip().lower() not in counts]
    if unpublished:
        chosen = random.choice(unpublished)
        print(f"🎯 [Weighted Selection] Found {len(unpublished)} unpublished file(s). Selected NEW: '{chosen.name}'")
        return chosen

    # 2. Recirculation Mode using Weighted Average
    if allow_recirculation:
        weights = []
        for c in candidates:
            cnt = counts.get(c.name.strip().lower(), 0)
            w = max(1, 1000 // (3 ** min(cnt, 6)))
            weights.append(w)

        chosen = random.choices(candidates, weights=weights, k=1)[0]
        used_times = counts.get(chosen.name.strip().lower(), 0)
        chosen_weight = max(1, 1000 // (3 ** min(used_times, 6)))
        total_w = sum(weights)
        pct = (chosen_weight / total_w) * 100
        print(f"🔁 [Weighted Selection] Recirculation Mode: Selected '{chosen.name}' (used {used_times} times before | weight: {chosen_weight}/{total_w} ~ {pct:.1f}%).")
        return chosen

    return None

def select_music_weighted_lru(music_files: list, history: list):
    """
    Selects background music track using Weighted LRU to ensure even rotation across all available tracks.
    """
    if not music_files:
        return None

    counts = {}
    for entry in history:
        track = entry.get("music", "")
        if track:
            counts[track.strip().lower()] = counts.get(track.strip().lower(), 0) + 1

    unplayed = [f for f in music_files if f.name.strip().lower() not in counts]
    if unplayed:
        chosen = random.choice(unplayed)
        print(f"🎵 [Music Selection] Selected unplayed track: '{chosen.name}'")
        return chosen

    weights = [max(1, 1000 // (3 ** min(counts.get(f.name.strip().lower(), 0), 6))) for f in music_files]
    chosen = random.choices(music_files, weights=weights, k=1)[0]
    used = counts.get(chosen.name.strip().lower(), 0)
    print(f"🎵 [Music Selection] Recirculated track: '{chosen.name}' (used {used} times before).")
    return chosen

def run_pipeline(publish: bool = True, force: bool = False, use_bgm: bool = False):
    print("\n" + "=" * 65)
    print("🎬 STARTING VIZ-REELS AUTOMATION CYCLE (DAILY PUBLISH)")
    print("=" * 65)

    # 1. Sync from Google Drive if Service Account is configured
    if os.environ.get("GOOGLE_SERVICE_ACCOUNT_KEY"):
        try:
            print("\n☁️ [Step 1] Syncing assets from Google Drive...")
            sync_all()
        except Exception as e:
            print(f"⚠️ Google Drive sync warning: {e}")
    else:
        print("\nℹ️ [Step 1] GOOGLE_SERVICE_ACCOUNT_KEY not set. Using local html_sources/ assets.")

    # 2. Select HTML file using Weighted Average / LRU
    html_files = sorted(list(HTML_DIR.glob("*.html")))
    if not html_files:
        print("❌ No HTML files found in html_sources/!")
        return

    history = load_history()

    if force:
        target_file = random.choice(html_files)
        print(f"\n🎯 [Step 2] Forced selection: '{target_file.name}'")
    else:
        print("\n⚖️ [Step 2] Evaluating candidates via Weighted Average / LRU...")
        target_file = select_candidate_weighted_lru(html_files, history, allow_recirculation=True)

    if not target_file:
        print("❌ Could not select a valid HTML file.")
        return

    topic_title = clean_filename_to_title(target_file.name)
    print(f"🎯 [Step 2] Active Topic: '{topic_title}' ({target_file.name})")

    # Select background music track via Weighted LRU if BGM is enabled
    chosen_music = None
    music_files = sorted(list(MUSIC_DIR.glob("*.mp3")) + list(MUSIC_DIR.glob("*.wav")))
    if use_bgm and music_files:
        chosen_music = select_music_weighted_lru(music_files, history)

    # 3. Generate AI Metadata with Pollinations AI
    print("\n🧠 [Step 3] Generating AI metadata via Pollinations AI...")
    metadata = generate_ai_metadata(topic_title, html_file_path=target_file)
    METADATA_FILE.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"✅ Metadata saved to metadata.json (Title: '{metadata.get('title')}')")

    # 4. Render 1080p 60FPS Video with Native Web Audio SFX
    print("\n📹 [Step 4] Rendering vertical video with native Web Audio SFX (1080x1920 @ 60FPS)...")
    video_path = convert_html_to_video(target_file, audio_path=chosen_music, handle="@kreggscode")
    print(f"✅ Video render complete: {video_path.name}")

    # 5. Upload to Facebook and Instagram
    if publish:
        print("\n🌐 [Step 5] Publishing to social media platforms...")
        publish_res = publish_video(video_path, metadata)
    else:
        print("\nℹ️ [Step 5] Skipping social publish (run with --publish to upload).")
        publish_res = {"status": "skipped"}

    # 6. Update History with ISO timestamp and full metadata
    now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    history.append({
        "file": target_file.name,
        "title": metadata.get("title"),
        "video": video_path.name,
        "music": chosen_music.name if chosen_music else None,
        "timestamp": now_iso,
        "publish": publish_res
    })
    save_history(history)

    print("\n" + "=" * 65)
    print(f"✅ VIZ-REEL CYCLE COMPLETED SUCCESSFULLY AT {now_iso}!")
    print("=" * 65 + "\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Full Automation Pipeline Orchestrator for Viz-Reels")
    parser.add_argument("--publish", action="store_true", help="Publish generated video to social media")
    parser.add_argument("--force", action="store_true", help="Force process even if already in history")
    parser.add_argument("--bgm", action="store_true", help="Mix subtle background music bed under sound effects")
    args = parser.parse_args()

    run_pipeline(publish=args.publish, force=args.force, use_bgm=args.bgm)
