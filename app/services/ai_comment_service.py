import random
import re
from typing import List

import httpx

from app.core.config import settings


SYSTEM_PROMPT = """
You write natural YouTube comments that feel like they were written by a real viewer.

Rules:
- Return exactly 3 comments
- Each comment must be on its own line
- Do not add any intro sentence
- Do not write labels like Comment 1, Comment 2, or Comment 3
- Do not use bullet points
- Do not use numbering
- Do not use quotation marks
- Do not use hashtags
- Use 0 or 1 emoji maximum per comment
- Keep each comment between 8 and 28 words
- Make comments sound warm, believable, and human
- Make comments clearly connected to the specific video
- Use real details from the title or description when possible
- Avoid generic phrases like:
  nice video
  great content
  very helpful
  thanks for sharing
  keep it up
- Do not ask for follow back, support back, subscribe back, or channel check
"""


RULE_BASED_COMMENTS = [
    "The way you explained this made it feel much easier to follow than I expected",
    "I liked how clear and watchable this felt from the beginning to the end",
    "This felt a lot more thoughtful than most videos I come across in this niche",
    "You have a really natural way of making the topic feel easy to stay with",
    "I clicked for the idea and stayed because the pacing was actually really good 👀",
    "This felt specific in a good way and not just thrown together for views",
    "There is something really easy to connect with in the way you present things",
    "This made the topic feel much more approachable without watering it down",
]


BANNED_PATTERNS = [
    r"\bnice video\b",
    r"\bgreat content\b",
    r"\bvery helpful\b",
    r"\bthanks for sharing\b",
    r"\bkeep it up\b",
    r"\bsubscribe back\b",
    r"\bsub back\b",
    r"\bfollow me\b",
    r"\bcheck my channel\b",
    r"\bcheck out my channel\b",
    r"\bcheck out my page\b",
]


INTRO_PATTERNS = [
    r"^here are\b",
    r"^here's\b",
    r"^below are\b",
    r"^these are\b",
    r"^youtube comments\b",
    r"^three natural\b",
    r"^three short\b",
]


def shorten_text(value: str, limit: int = 500) -> str:
    if not value:
        return ""
    value = re.sub(r"\s+", " ", value).strip()
    return value[:limit]


def clean_comment_line(text: str) -> str:
    value = (text or "").strip()

    value = re.sub(r"^\s*[-*•]+\s*", "", value)
    value = re.sub(r"^\s*\d+[.)]\s*", "", value)
    value = re.sub(r"^\s*comment\s*\d+\s*[:.-]?\s*", "", value, flags=re.IGNORECASE)

    value = value.replace('"', "")
    value = value.replace("“", "")
    value = value.replace("”", "")
    value = value.replace("‘", "")
    value = value.replace("’", "")

    value = re.sub(r"\s+", " ", value).strip()

    lowered = value.lower()
    for pattern in INTRO_PATTERNS:
        if re.search(pattern, lowered):
            return ""

    return value


def looks_spammy(text: str) -> bool:
    lowered = text.lower().strip()
    return any(re.search(pattern, lowered) for pattern in BANNED_PATTERNS)


def is_reasonable_length(text: str) -> bool:
    words = text.split()
    return 8 <= len(words) <= 28


def normalize_comments(raw_comments: List[str]) -> List[str]:
    cleaned: List[str] = []
    seen = set()

    for item in raw_comments:
        value = clean_comment_line(item)

        if not value:
            continue

        if looks_spammy(value):
            continue

        if not is_reasonable_length(value):
            continue

        key = value.lower()
        if key in seen:
            continue

        seen.add(key)
        cleaned.append(value)

    return cleaned[:3]


def split_possible_comments(text: str) -> List[str]:
    if not text:
        return []

    text = text.strip()

    numbered_chunks = re.split(r"(?:^|\n)\s*(?:comment\s*\d+\s*:|\d+[.)]\s+)", text, flags=re.IGNORECASE)
    numbered_chunks = [chunk.strip() for chunk in numbered_chunks if chunk.strip()]
    if len(numbered_chunks) >= 3:
        return numbered_chunks

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if len(lines) >= 3:
        return lines

    sentence_chunks = re.split(r"(?<=[.!?])\s+(?=[A-Z])", text)
    sentence_chunks = [chunk.strip() for chunk in sentence_chunks if chunk.strip()]
    return sentence_chunks


def extract_comments_from_text(text: str) -> List[str]:
    if not text:
        return []

    chunks = split_possible_comments(text)
    comments = normalize_comments(chunks)

    if len(comments) >= 3:
        return comments[:3]

    lines = [clean_comment_line(line) for line in text.splitlines() if line.strip()]
    lines = [line for line in lines if line]
    comments = normalize_comments(lines)

    if len(comments) >= 3:
        return comments[:3]

    return comments[:3]


def build_comment_prompt(video) -> str:
    title = shorten_text(getattr(video, "title", "") or "", 200)
    description = shorten_text(getattr(video, "description", "") or "", 600)
    niche = (getattr(video, "niche", "") or "").strip()
    channel_name = (getattr(video, "channel_name", "") or "").strip()

    return f"""
Video title: {title}
Video description: {description}
Channel name: {channel_name}
Niche: {niche}

Write exactly 3 natural YouTube comments for this specific video.

Important:
- Each comment must be on its own line
- No intro line
- No labels
- No numbering
- Make the comments specific to this video
- Mention a concrete topic, detail, step, mood, or angle from the title or description when possible
- Sound human and natural
"""


def generate_with_ollama(video) -> List[str]:
    payload = {
        "model": settings.OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_comment_prompt(video)},
        ],
        "stream": False,
    }

    urls = [
        f"{settings.OLLAMA_BASE_URL}/api/chat",
        f"{settings.OLLAMA_BASE_URL}/v1/chat/completions",
    ]

    with httpx.Client(timeout=90.0) as client:
        for url in urls:
            try:
                response = client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()

                text = ""

                if isinstance(data.get("message"), dict):
                    text = data["message"].get("content", "") or ""
                elif data.get("choices"):
                    choice = data["choices"][0]
                    if isinstance(choice.get("message"), dict):
                        text = choice["message"].get("content", "") or ""

                comments = extract_comments_from_text(text)
                if comments:
                    return comments
            except Exception as exc:
                print(f"Ollama call failed for {url}: {exc}")
                continue

    return []


def generate_rule_based_comments(video) -> List[str]:
    title = ((getattr(video, "title", "") or "") + " " + (getattr(video, "description", "") or "")).lower()
    niche = (getattr(video, "niche", "") or "").lower()

    specific: List[str] = []

    if "pasta" in title:
        specific.extend([
            "The part with the pasta timing made this feel a lot more doable for a busy weeknight",
            "I liked how simple this pasta recipe felt without making it seem boring at all 🍝",
        ])

    if "recipe" in title or niche == "food":
        specific.extend([
            "The way you showed the steps made this recipe feel realistic enough to actually try",
            "I liked that this recipe felt practical and still really satisfying to watch",
        ])

    if "workout" in title or niche == "fitness":
        specific.extend([
            "This workout felt realistic enough to actually come back to instead of trying once and quitting",
            "I liked how direct and motivating this felt without becoming too intense",
        ])

    if "makeup" in title or "skincare" in title or niche == "beauty":
        specific.extend([
            "I liked how approachable this look felt instead of making everything seem impossible to recreate",
            "The way you explained the routine made it feel much more wearable and real",
        ])

    if "python" in title or "fastapi" in title or niche == "coding":
        specific.extend([
            "The way you broke this down made the whole setup feel much less intimidating",
            "I liked that this stayed practical instead of turning into an overly long explanation",
        ])

    if "travel" in title or "vlog" in title or niche == "travel":
        specific.extend([
            "The way you put this together made the whole vlog feel really easy to stay with",
            "I liked how this captured the mood without trying too hard to force it 🌍",
        ])

    pool = specific + RULE_BASED_COMMENTS
    random.shuffle(pool)
    return normalize_comments(pool)[:3]


def ensure_three_comments(comments: List[str], video) -> List[str]:
    final_comments = normalize_comments(comments)

    if len(final_comments) >= 3:
        return final_comments[:3]

    fallback = generate_rule_based_comments(video)
    seen = {comment.lower() for comment in final_comments}

    for item in fallback:
        if len(final_comments) >= 3:
            break
        if item.lower() not in seen:
            final_comments.append(item)
            seen.add(item.lower())

    return final_comments[:3]


def generate_comments(video) -> List[str]:
    provider = (settings.LLM_PROVIDER or "rule_based").lower()

    if provider == "ollama":
        comments = generate_with_ollama(video)
        return ensure_three_comments(comments, video)

    return ensure_three_comments([], video)