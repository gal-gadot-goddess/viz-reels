"""
AI Metadata Generator for viz-reels via Pollinations AI
Generates engaging social media titles, Instagram captions, Facebook captions, and hashtags.
"""

import os
import sys
import re
import json
import urllib.request
import urllib.error
from pathlib import Path
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

def clean_filename_to_title(filename: str) -> str:
    name = Path(filename).stem
    # Remove leading numbers like 01-, 02-
    name = re.sub(r'^[0-9]+[-_ ]*', '', name)
    name = name.replace("_", " ").replace("-", " ")
    return " ".join(name.split())

def generate_ai_metadata(topic: str) -> dict:
    api_key = os.environ.get("POLLINATIONS_API_KEY", "")
    model = os.environ.get("AI_MODEL", "gemini-fast")

    fallback_metadata = {
        "title": f"{topic} Explained in 20 Seconds!",
        "ig_caption": f"⚡ {topic} Visualized! Which one do you prefer in your stack? Drop your thoughts below! 👇\n\nFollow @kreggscode for daily visual system design & architecture reels. ✨\n\n#SoftwareEngineering #SystemDesign #Tech #WebDev #Coding #Developers",
        "fb_caption": f"Architecture breakdown: {topic}.\n\nUnderstanding the exact mechanical trade-offs is crucial for high-scale backend engineering.\n\nWhich approach has served your projects best? Let's discuss in the comments!\n\n#Programming #SoftwareEngineering #Backend #SystemDesign #Code",
        "threads_caption": f"{topic} in 20s. What's your go-to architecture choice? #tech #coding",
        "hashtags": ["#Tech", "#Programming", "#Coding", "#SystemDesign", "#SoftwareEngineering", "#WebDev", "#LearnToCode"]
    }

    url = "https://text.pollinations.ai/openai"
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Antigravity-Agent"
    }
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    prompt = f"""You are a viral social media engineer specializing in technical visual reels for developers, programmers, and software architects (@kreggscode).
The user is sharing a dynamic, visual animated comparison / concept reel on: "{topic}".

Produce a high-engagement JSON response with:
1. "title": Punchy, click-worthy hook title (max 60 chars) with emojis.
2. "ig_caption": High-retention Instagram caption formatted with clean whitespace, bullet points explaining the core architectural concept, engaging hook at the top, clear takeaways, and a call-to-action asking viewers to comment.
3. "fb_caption": In-depth professional Facebook caption breaking down the engineering trade-offs, advantages, and real-world production advice.
4. "threads_caption": Short, provocative summary (max 300 chars) for Threads.
5. "hashtags": Array of 7-10 trending tags (#SystemDesign, #Backend, #Coding, #Tech, etc.).

Return ONLY the raw JSON object. Do not wrap in markdown or backticks."""

    payload = {
        "messages": [
            {"role": "system", "content": "You output strictly valid JSON without explanation or formatting wrappers."},
            {"role": "user", "content": prompt}
        ],
        "model": model,
        "jsonMode": True
    }

    try:
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw_text = resp.read().decode("utf-8")
            raw_clean = re.sub(r"^```(?:json)?\s*", "", raw_text.strip(), flags=re.MULTILINE)
            raw_clean = re.sub(r"\s*```$", "", raw_clean, flags=re.MULTILINE).strip()
            data = json.loads(raw_clean)
            print("✅ Successfully generated AI metadata via Pollinations AI.")
            return data
    except Exception as e:
        print(f"⚠️ Pollinations AI notice ({e}). Using curated fallback metadata.")
        return fallback_metadata

if __name__ == "__main__":
    t = sys.argv[1] if len(sys.argv) > 1 else "Kafka vs RabbitMQ"
    print(json.dumps(generate_ai_metadata(t), indent=2, ensure_ascii=False))
