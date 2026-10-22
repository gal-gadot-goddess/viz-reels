"""
Viz-Reels Converter: HTML Animation + Native Web Audio SFX -> 1080x1920 60FPS Video
Engineered for 9:16 Vertical Video (Instagram Reels / Facebook Reels / YouTube Shorts)
Captures in-browser real-time Web Audio API synthesized sound effects and merges via FFmpeg.
"""

import os
import sys
import time
import math
import random
import re
import base64
import argparse
import subprocess
from pathlib import Path

# Ensure UTF-8 output on Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from playwright.sync_api import sync_playwright

BASE_DIR = Path(__file__).resolve().parent
HTML_DIR = BASE_DIR / "html_sources"
MUSIC_DIR = BASE_DIR / "music"
OUTPUT_DIR = BASE_DIR / "output"
TEMP_DIR = OUTPUT_DIR / ".temp_recordings"

def detect_duration(file_content: str, default_duration: float = 19.5) -> float:
    """
    Detects animation timeline duration from code or defaults to 19.5s for viz-reels.
    """
    # Look for last 'at(XX.XX, ...)' timestamp in buildTimeline
    at_matches = re.findall(r'at\s*\(\s*([0-9.]+)\s*,', file_content)
    if at_matches:
        last_t = max(float(x) for x in at_matches)
        dur = last_t + 2.0  # Allow 2 seconds hold for punchline / branding
        print(f"  [Duration] Detected from last timeline event ({last_t:.2f}s): {dur:.2f}s")
        return dur

    # Look for DUR = XX
    dur_match = re.search(r'DUR\s*=\s*([0-9.]+)', file_content)
    if dur_match:
        val = float(dur_match.group(1))
        print(f"  [Duration] Detected from static 'DUR = {val}': {val:.2f}s")
        return val

    print(f"  [Duration] Using standard viz-reel duration: {default_duration:.2f}s")
    return default_duration

def convert_html_to_video(
    html_path: Path,
    output_mp4: Path = None,
    audio_path: Path = None,
    duration: float = None,
    handle: str = "@kreggscode",
    width: int = 1080,
    height: int = 1920,
    fps: int = 60,
    crf: int = 18
) -> Path:
    html_path = Path(html_path).resolve()
    if not html_path.exists():
        raise FileNotFoundError(f"HTML file not found: {html_path}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if output_mp4 is None:
        output_mp4 = OUTPUT_DIR / f"{html_path.stem}.mp4"
    else:
        output_mp4 = Path(output_mp4).resolve()

    file_content = html_path.read_text(encoding="utf-8", errors="ignore")
    if duration is None:
        duration = detect_duration(file_content)

    temp_rec_dir = OUTPUT_DIR / f".rec_{html_path.stem}"
    temp_rec_dir.mkdir(parents=True, exist_ok=True)

    file_uri = f"file:///{html_path.as_posix()}"

    print(f"\n{'=' * 65}")
    print(f"🎬 RENDERING VIZ-REEL: {html_path.name}")
    print(f"📐 Target: {width}x{height} @ {fps} FPS (9:16 Vertical)")
    print(f"⏱️ Duration: {duration:.2f}s | CRF: {crf}")
    print(f"🔊 Capturing native Web Audio API sound effects")
    print(f"{'=' * 65}")

    # 1. Launch Playwright with AudioContext hook
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--autoplay-policy=no-user-gesture-required",
                "--no-sandbox",
                "--disable-web-security"
            ]
        )
        context = browser.new_context(
            viewport={"width": width, "height": height},
            device_scale_factor=1,
            record_video_dir=str(temp_rec_dir),
            record_video_size={"width": width, "height": height}
        )
        page = context.new_page()

        # Injected Web Audio capture hook
        page.add_init_script("""
        window.__audioChunks = [];
        window.__audioRecorder = null;
        window.__capturedMime = 'audio/webm';

        const OrigAudioContext = window.AudioContext || window.webkitAudioContext;
        if (OrigAudioContext) {
            window.AudioContext = class extends OrigAudioContext {
                constructor(...args) {
                    super(...args);
                    window.__ctx = this;
                    
                    if (this.state === 'suspended') {
                        this.resume().catch(()=>{});
                    }
                    this.addEventListener('statechange', () => {
                        if (this.state === 'suspended') this.resume().catch(()=>{});
                    });

                    const dest = this.createMediaStreamDestination();
                    this.__dest = dest;

                    const origConnect = AudioNode.prototype.connect;
                    AudioNode.prototype.connect = function(target, ...rest) {
                        if (target === this.context.destination && this.context.__dest) {
                            try { origConnect.call(this, this.context.__dest, ...rest); } catch(e){}
                        }
                        return origConnect.call(this, target, ...rest);
                    };

                    try {
                        const mime = MediaRecorder.isTypeSupported('audio/webm;codecs=opus') ? 'audio/webm;codecs=opus' : 'audio/webm';
                        window.__capturedMime = mime;
                        const rec = new MediaRecorder(dest.stream, { mimeType: mime });
                        window.__audioRecorder = rec;
                        rec.ondataavailable = e => {
                            if (e.data && e.data.size > 0) window.__audioChunks.push(e.data);
                        };
                        rec.start(50);
                    } catch(e) {
                        console.error('[AudioHook] MediaRecorder failed:', e);
                    }
                }
            };
            window.webkitAudioContext = window.AudioContext;
        }
        """)

        page.goto(file_uri, wait_until="load")

        # Hide interactive replay/mute buttons
        page.add_style_tag(content="""
            #mute, #replayBtn, .ctl {
                display: none !important;
                opacity: 0 !important;
                visibility: hidden !important;
                pointer-events: none !important;
            }
        """)

        # Set branding handle
        if handle:
            page.evaluate(f"""(handle) => {{
                document.querySelectorAll('.brand, #brand2').forEach(el => {{
                    el.textContent = handle;
                }});
            }}""", handle)

        # Wait for Google Fonts to be ready
        try:
            page.evaluate("() => document.fonts.ready")
        except Exception:
            pass

        # Trigger clean start from t=0
        page.evaluate("""() => {
            if (window.__ctx && window.__ctx.state === 'suspended') {
                window.__ctx.resume();
            }
            if (typeof startPlay === 'function') {
                startPlay();
            } else if (typeof restart === 'function') {
                restart();
            } else if (typeof start === 'function') {
                start();
            }
        }""")

        print(f"⏺️  Recording visual frames + Web Audio for {duration:.2f}s...")
        time.sleep(duration)

        # Retrieve captured sound effects audio stream
        sfx_b64 = page.evaluate("""async () => {
            if (!window.__audioRecorder || window.__audioChunks.length === 0) return null;
            if (window.__audioRecorder.state !== 'inactive') {
                window.__audioRecorder.stop();
            }
            await new Promise(r => setTimeout(r, 200));
            const blob = new Blob(window.__audioChunks, { type: window.__capturedMime });
            const reader = new FileReader();
            return new Promise(resolve => {
                reader.onloadend = () => {
                    const b64 = reader.result.split(',')[1];
                    resolve(b64);
                };
                reader.readAsDataURL(blob);
            });
        }""")

        page.close()
        context.close()
        browser.close()

    # 2. Locate recorded raw video
    recorded_videos = list(temp_rec_dir.glob("*.webm"))
    if not recorded_videos:
        raise RuntimeError("Recording failed - no raw .webm video found.")
    raw_video = recorded_videos[0]

    # 3. Save captured SFX audio
    sfx_audio_path = temp_rec_dir / "sfx.webm"
    has_sfx = False
    if sfx_b64:
        audio_bytes = base64.b64decode(sfx_b64)
        if len(audio_bytes) > 1000:
            sfx_audio_path.write_bytes(audio_bytes)
            has_sfx = True
            print(f"✅ Extracted native SFX audio: {len(audio_bytes) / 1024:.1f} KB")

    fade_start = max(0.0, duration - 0.5)

    # 4. FFmpeg Muxing: Video + SFX + (Optional BGM bed)
    print("⚡ Encoding high-quality MP4 with FFmpeg...")

    if has_sfx and audio_path and Path(audio_path).exists():
        # Mix SFX (loud) + BGM (subtle bed at 20%)
        print(f"🎵 Mixing background track bed: {Path(audio_path).name} (ducked to 20%)")
        ffmpeg_cmd = [
            "ffmpeg", "-y",
            "-i", str(raw_video),
            "-i", str(sfx_audio_path),
            "-stream_loop", "-1",
            "-i", str(audio_path),
            "-filter_complex",
            f"[1:a]volume=1.0[sfx];[2:a]volume=0.20[bgm];[sfx][bgm]amix=inputs=2:duration=first,afade=t=out:st={fade_start:.2f}:d=0.5[aout]",
            "-map", "0:v:0",
            "-map", "[aout]",
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", str(crf),
            "-pix_fmt", "yuv420p",
            "-r", str(fps),
            "-c:a", "aac",
            "-b:a", "192k",
            "-t", str(duration),
            str(output_mp4)
        ]
    elif has_sfx:
        # Native SFX only
        ffmpeg_cmd = [
            "ffmpeg", "-y",
            "-i", str(raw_video),
            "-i", str(sfx_audio_path),
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", str(crf),
            "-pix_fmt", "yuv420p",
            "-r", str(fps),
            "-c:a", "aac",
            "-b:a", "192k",
            "-af", f"afade=t=out:st={fade_start:.2f}:d=0.5",
            "-t", str(duration),
            str(output_mp4)
        ]
    elif audio_path and Path(audio_path).exists():
        # Fallback to looping music only
        ffmpeg_cmd = [
            "ffmpeg", "-y",
            "-i", str(raw_video),
            "-stream_loop", "-1",
            "-i", str(audio_path),
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", str(crf),
            "-pix_fmt", "yuv420p",
            "-r", str(fps),
            "-c:a", "aac",
            "-b:a", "192k",
            "-af", f"afade=t=out:st={fade_start:.2f}:d=0.5",
            "-t", str(duration),
            str(output_mp4)
        ]
    else:
        # Video only
        ffmpeg_cmd = [
            "ffmpeg", "-y",
            "-i", str(raw_video),
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", str(crf),
            "-pix_fmt", "yuv420p",
            "-r", str(fps),
            "-t", str(duration),
            str(output_mp4)
        ]

    subprocess.check_call(ffmpeg_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # Clean up temp recordings
    try:
        for f in temp_rec_dir.glob("*"):
            f.unlink()
        temp_rec_dir.rmdir()
    except Exception:
        pass

    # Extract high-clarity cover thumbnail from the near-end of the animation (e.g. duration - 1.2s)
    # At this timestamp, the entire architectural diagram, comparison, and labels are fully rendered.
    thumb_time = max(1.0, duration - 1.2)
    thumb_path = output_mp4.with_suffix(".jpg")
    thumb_cmd = [
        "ffmpeg", "-y",
        "-ss", f"{thumb_time:.2f}",
        "-i", str(output_mp4),
        "-frames:v", "1",
        "-update", "1",
        "-q:v", "2",
        str(thumb_path)
    ]
    try:
        subprocess.check_call(thumb_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"🖼️ Cover thumbnail generated: {thumb_path.name} (at {thumb_time:.2f}s)")
    except Exception as e:
        print(f"⚠️ Thumbnail generation notice: {e}")

    size_mb = output_mp4.stat().st_size / (1024 * 1024)
    print(f"🎉 Complete! Saved to: {output_mp4.name}")
    print(f"📦 Size: {size_mb:.2f} MB | Duration: {duration:.2f}s | Resolution: {width}x{height} @ {fps}fps")
    print(f"{'=' * 65}\n")
    return output_mp4

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert Viz-Reels HTML animations to 9:16 Video with Web Audio SFX")
    parser.add_argument("html_file", help="Path to HTML file to convert")
    parser.add_argument("-o", "--output", help="Output MP4 path")
    parser.add_argument("-d", "--duration", type=float, help="Explicit duration in seconds")
    parser.add_argument("--handle", default="@kreggscode", help="Branding handle (default: @kreggscode)")
    parser.add_argument("--bgm", help="Optional background music file to mix with sound effects")
    args = parser.parse_args()

    convert_html_to_video(args.html_file, output_mp4=args.output, duration=args.duration, handle=args.handle, audio_path=args.bgm)
