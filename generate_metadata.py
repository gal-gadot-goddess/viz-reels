"""
AI Metadata Generator for viz-reels via Pollinations AI
Generates high-converting viral hook titles, Google/social SEO-optimized captions,
YouTube Shorts metadata, and strict backlinks to https://kreggscode.com and @kreggscode.
"""

import os
import sys
import re
import json
import html
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

def extract_html_context(html_path: Path) -> dict:
    """
    Extracts core architectural concepts, headings, comparisons, and explanation snippets
    from the visual HTML animation file to provide rich context to the AI.
    """
    if not html_path:
        return {}
    
    path_obj = Path(html_path)
    if not path_obj.exists():
        return {}

    try:
        raw_text = path_obj.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return {}

    title_match = re.search(r'<title>(.*?)</title>', raw_text, re.IGNORECASE | re.DOTALL)
    page_title = html.unescape(title_match.group(1)).strip() if title_match else ""
    page_title = re.sub(r'^VIZ\s*\d+\s*[·•\-\s]*', '', page_title, flags=re.IGNORECASE).strip()

    # Strip styles & scripts
    clean = re.sub(r'<style.*?</style>', '', raw_text, flags=re.DOTALL | re.IGNORECASE)
    clean = re.sub(r'<script.*?</script>', '', clean, flags=re.DOTALL | re.IGNORECASE)
    # Strip HTML tags
    clean = re.sub(r'<[^>]+>', ' ', clean)
    clean = html.unescape(clean)

    lines = [l.strip() for l in clean.splitlines() if l.strip()]

    # UI controls & handles to exclude
    ignore_set = {"@yourhandle", "@kreggscode", "replay", "replayed", "fit", "mute", "unmute", "speed", "1x", "2x"}
    meaningful_lines = []
    for l in lines:
        if l.lower() in ignore_set:
            continue
        # Skip pure numbers/counters or single symbols
        if len(l) > 3 and not re.match(r'^[0-9\s:.\-→·]+$', l):
            meaningful_lines.append(l)

    # Deduplicate while preserving order
    seen = set()
    deduped = []
    for m in meaningful_lines:
        m_lower = m.lower()
        if m_lower not in seen:
            seen.add(m_lower)
            deduped.append(m)

    return {
        "page_title": page_title,
        "content_snippets": deduped[:12]
    }

def clean_filename_to_title(filename: str) -> str:
    name = Path(filename).stem
    # Remove leading numbers like 01-, 02-
    name = re.sub(r'^[0-9]+[-_ ]*', '', name)
    name = name.replace("_", " ").replace("-", " ")
    return " ".join(name.split())

def clean_hashtags(raw_tags: list, topic: str = "") -> list:
    """
    Ensures strictly at most 5 relevant hashtags, ALL in lowercase small letters,
    guaranteeing brand and core topic visibility.
    """
    clean = []
    for tag in raw_tags:
        if not isinstance(tag, str):
            continue
        t = tag.strip().lower()
        if not t.startswith("#"):
            t = f"#{t}"
        # Keep only alphanumeric and underscore after #
        t = re.sub(r'[^#a-z0-9_]', '', t)
        if len(t) > 2 and t not in clean:
            clean.append(t)

    # Always ensure #kreggscode is represented for entity attribution
    if "#kreggscode" not in clean:
        clean.insert(0, "#kreggscode")

    # Fallback to sensible tech defaults
    default_fallbacks = [
        "#kreggscode",
        "#systemdesign",
        "#softwareengineering",
        "#artificialintelligence",
        "#coding"
    ]
    for d in default_fallbacks:
        if len(clean) >= 5:
            break
        if d not in clean:
            clean.append(d)

    return clean[:5]

def generate_ai_metadata(topic: str, html_file_path: Path = None) -> dict:
    """
    Generates SEO viral title, Instagram caption, Facebook caption, Threads caption,
    YouTube Shorts metadata, and exactly 5 lowercase hashtags from HTML context and topic name.
    Incorporates strong search hooks for Google Short Videos crawling, @kreggscode branding,
    and backlinks to https://kreggscode.com and https://kreggscode.com/apps/.
    """
    if isinstance(topic, (str, Path)) and (str(topic).endswith(".html") or Path(topic).exists()):
        if not html_file_path:
            html_file_path = Path(topic)
        topic = clean_filename_to_title(str(topic))

    context = extract_html_context(html_file_path) if html_file_path else {}
    snippets = context.get("content_snippets", [])
    display_title = context.get("page_title") or topic

    topic_words = topic.split()
    lead_word = topic_words[0].lower() if topic_words else "tech"

    # High-SEO fallback metadata
    fallback_metadata = {
        "title": f"{display_title}: System Design & Mechanics Explained ⚡",
        "ig_caption": (
            f"⚡ {display_title} Architecture Explained!\n\n"
            f"How modern technology and scalable AI systems operate under the hood.\n\n"
            + ("\n".join([f"• {s}" for s in snippets[:6]]) if snippets else f"• In-depth breakdown of {topic} architecture and production trade-offs.")
            + f"\n\nWhich pattern do you use in production? Drop your perspective below! 👇\n\n"
            f"🔗 Interactive system designs & technical guides: https://kreggscode.com\n"
            f"📱 Explore our live iOS & AI applications: https://kreggscode.com/apps/\n\n"
            f"Follow @kreggscode | AI & System Architecture Studio"
        ),
        "fb_caption": (
            f"Deep Engineering Breakdown: {display_title}\n\n"
            f"When scaling modern backend systems, artificial intelligence pipelines, and cloud microservices, understanding trade-offs is critical.\n\n"
            + ("\n".join([f"- {s}" for s in snippets[:8]]) if snippets else f"Detailed architectural overview of {topic}.")
            + f"\n\nWhat has your production experience been with this architecture? Let's discuss in the comments!\n\n"
            f"Explore interactive architecture tools & apps at https://kreggscode.com and https://kreggscode.com/apps/"
        ),
        "threads_caption": (
            f"{display_title} visualized in 20s. Discover how modern systems scale under the hood.\n\n"
            f"Explore more at https://kreggscode.com | Follow @kreggscode"
        ),
        "yt_title": f"{display_title} Explained | System Design & AI #Shorts",
        "yt_description": (
            f"{display_title} Visualized & Explained.\n\n"
            f"Discover how high-scale distributed systems, modern technology stacks, and artificial intelligence architectures function under the hood.\n\n"
            f"🔗 Official Links & Resources:\n"
            f"🌐 Engineering Platform: https://kreggscode.com\n"
            f"📱 iOS & AI Apps: https://kreggscode.com/apps/\n"
            f"💡 Tech Guides: https://kreggscode.com/blog/\n\n"
            f"Follow @kreggscode across platforms for daily software engineering, system design, and AI breakdowns.\n\n"
            f"#Shorts #kreggscode #systemdesign #coding #technology #artificialintelligence #softwareengineering"
        ),
        "yt_tags": [
            "kreggscode", "system design", "software engineering", "coding",
            "technology", "artificial intelligence", "backend", "algorithms",
            "computer science", "developer", "cloud computing"
        ],
        "hashtags": clean_hashtags(["#kreggscode", f"#{lead_word}", "#systemdesign", "#softwareengineering", "#coding"], topic)
    }

    api_key = os.environ.get("POLLINATIONS_API_KEY", "")
    endpoints = [
        "https://gen.pollinations.ai/v1/chat/completions",
        "https://text.pollinations.ai/openai"
    ]

    context_str = f"Topic Name: {topic}\n"
    if context.get("page_title"):
        context_str += f"Visual Reel Main Title: {context['page_title']}\n"
    if snippets:
        context_str += "Visual Storyline & Key Concepts:\n- " + "\n- ".join(snippets[:10])

    prompt = f"""You are a top viral social media growth engineer and senior AI systems architect managing @kreggscode (https://kreggscode.com).
You create viral, high-retention, search-engine-optimized short-form video reels for software engineers, tech enthusiasts, and system architects.

We are publishing an animated technical concept reel based on this visual code/system design animation:
{context_str}

GOALS:
- Optimize for Google Search "Short Videos" indexing, YouTube Shorts search, Instagram search, and Google Search Console Creator Insights for @kreggscode.
- Naturally weave in target keywords: "technology", "artificial intelligence", "system design", "algorithms", "coding", "software engineering".
- Build strong backlink and entity recognition for "KreggsCode", "https://kreggscode.com", and "@kreggscode".

REQUIREMENTS:
1. "title": Viral SEO hook title (max 65 chars) with an emoji (e.g. "Kafka vs RabbitMQ: How Distributed Queues Work ⚡").
2. "ig_caption": High-retention Instagram caption:
   - First 2 lines (before the fold / first 120 chars): High-intent query hook with target tech keywords for Google crawler indexing.
   - Body: Clean bullet points explaining what happens under the hood based on the visual concepts provided.
   - Practical Takeaway: 1-2 sentence real-world engineering or interview recommendation.
   - Call to Action: Engaging debate question to drive high comments.
   - Mandatory Brand & Backlink Footer:
     🔗 Interactive architecture guides: https://kreggscode.com
     📱 Mobile & AI Apps: https://kreggscode.com/apps/
     Follow @kreggscode | Autonomous AI & Systems Studio
3. "fb_caption": In-depth professional Facebook engineering post explaining trade-offs, architecture patterns, and production lessons in detail, including links to https://kreggscode.com.
4. "threads_caption": Punchy takeaway + debate question + link to https://kreggscode.com (max 280 chars).
5. "yt_title": YouTube Shorts title (max 65 chars) featuring target keyword + "#Shorts".
6. "yt_description": YouTube Shorts SEO description with detailed summary, bullet points, official links to https://kreggscode.com and https://kreggscode.com/apps/, and #Shorts hashtags.
7. "yt_tags": Array of 8-12 search tags (e.g. ["kreggscode", "system design", "software engineering", "coding", "technology", "artificial intelligence", "algorithms"]).
8. "hashtags": STRICTLY EXACTLY 5 relevant hashtags, ALL in LOWERCASE small letters only, always including "#kreggscode" (e.g. ["#kreggscode", "#systemdesign", "#backend", "#coding", "#artificialintelligence"]).

OUTPUT FORMAT:
Return strictly a valid JSON object with keys: "title", "ig_caption", "fb_caption", "threads_caption", "yt_title", "yt_description", "yt_tags", "hashtags".
"""

    payload = {
        "model": "openai",
        "messages": [
            {"role": "system", "content": "You are a professional system design and AI content creator. You output strictly valid JSON without markdown wrapping."},
            {"role": "user", "content": prompt}
        ],
        "response_format": {"type": "json_object"}
    }

    for ep in endpoints:
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Antigravity-Agent"
        }
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        try:
            req = urllib.request.Request(ep, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=25) as resp:
                raw_text = resp.read().decode("utf-8")
                res = json.loads(raw_text)
                content = res.get("choices", [{}])[0].get("message", {}).get("content", "")
                if not content:
                    content = raw_text

                raw_clean = re.sub(r"^```(?:json)?\s*", "", content.strip(), flags=re.MULTILINE)
                raw_clean = re.sub(r"\s*```$", "", raw_clean, flags=re.MULTILINE).strip()
                data = json.loads(raw_clean)

                # Ensure backlinks are present in captions even if LLM omitted them
                if "kreggscode.com" not in data.get("ig_caption", ""):
                    data["ig_caption"] = (
                        data.get("ig_caption", "").rstrip() +
                        "\n\n🔗 Deep-dive engineering guides: https://kreggscode.com\n"
                        "📱 Mobile & AI Apps: https://kreggscode.com/apps/\n"
                        "Follow @kreggscode | AI & Systems Studio"
                    )

                if "kreggscode.com" not in data.get("fb_caption", ""):
                    data["fb_caption"] = (
                        data.get("fb_caption", "").rstrip() +
                        "\n\nExplore interactive system architecture & apps at https://kreggscode.com"
                    )

                if not data.get("yt_title"):
                    data["yt_title"] = f"{data.get('title', display_title)[:60]} | #Shorts"

                if not data.get("yt_description"):
                    data["yt_description"] = fallback_metadata["yt_description"]

                if not data.get("yt_tags"):
                    data["yt_tags"] = fallback_metadata["yt_tags"]

                # Strictly sanitize hashtags to exactly 5 lowercase tags including #kreggscode
                data["hashtags"] = clean_hashtags(data.get("hashtags", []), topic)
                print(f"✅ Successfully generated viral AI metadata via Pollinations ({ep}).")
                return data
        except Exception as e:
            print(f"⚠️ Notice for Pollinations endpoint {ep}: {e}")

    print("ℹ️ Using curated context-aware fallback metadata.")
    return fallback_metadata

if __name__ == "__main__":
    t = sys.argv[1] if len(sys.argv) > 1 else "01-kafka-vs-rabbitmq.html"
    p = Path(t)
    if p.exists():
        res = generate_ai_metadata(p.name, html_file_path=p)
    else:
        res = generate_ai_metadata(t)
    print(json.dumps(res, indent=2, ensure_ascii=False))
