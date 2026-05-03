import random
import re
from typing import List

import httpx

from app.core.config import settings


SYSTEM_PROMPT = """
You write natural YouTube comments that feel like they were written by a real viewer.

Main goals:
- Sound warm, believable, and human
- Feel clearly connected to the actual video
- Leave a memorable impression on the creator
- Indirectly increase the chance that the creator notices the commenter
- Make the creator feel seen, appreciated, and a little curious

Rules:
- Write exactly 3 comment options
- Each comment should feel like it came from someone who actually watched the video
- Use specific details from the title or description.
- Make comments feel personal and specific to this video, not generic enough to be used on any video.
- Use a few emojis if it fits the vibe, but don't overdo it.
- Mention a real topic, step, theme, moment, angle, or style from the video
- Avoid generic praise unless combined with something specific
- Comments should be supportive, natural, and slightly personal
- Keep comments between 8 and 28 words
- No bullet points
- No dashes
- No numbering
- No quotation marks
- No hashtags
- Use 0 or 1 emoji per comment
- Not every comment should include an emoji
- Do not self-promote
- Do not ask for follow back, subscribe back, support back, or channel check
- Avoid robotic phrases and generic phrases like:
  great content
  valuable content
  amazing video
  nice video
  very helpful
  thanks for sharing
  keep it up
- Make the 3 comments clearly different from each other
"""


RULE_BASED_COMMENTS = [
    "The way you structured this made it feel much easier to follow than I expected",
    "I liked how specific this felt instead of dragging everything out for no reason",
    "This was such a solid first video to land on from your channel honestly",
    "You have a way of explaining things that makes people want to stay a little longer",
    "This felt much more intentional than most videos I come across in this niche",
    "I clicked for the topic but the pacing is what made me keep watching 👀",
    "There’s something really watchable about the way you put these videos together",
    "This made the whole topic feel more approachable without watering it down",
    "The clarity in this really stands out fast, especially in this niche",
]


BANNED_PATTERNS = [
    r"\bgreat content\b",
    r"\bvaluable content\b",
    r"\bthanks for sharing\b",
    r"\bkeep it up\b",
    r"\bamazing video\b",
    r"\bnice video\b",
    r"\bvery helpful\b",
    r"\bsupport me too\b",
    r"\bsub back\b",
    r"\bsubscribe back\b",
    r"\bcheck my channel\b",
    r"\bcheck out my channel\b",
    r"\bcheck out my page\b",
    r"\bvisit my channel\b",
    r"\bvisit my page\b",
    r"\bfollow me\b",
]


INTRO_PATTERNS = [
    r"^here are\b",
    r"^here's\b",
    r"^below are\b",
    r"^these are\b",
    r"^three natural youtube comments\b",
    r"^youtube comments for\b",
]


GENERIC_PATTERNS = [
    r"\bnice video\b",
    r"\bgreat video\b",
    r"\bgreat content\b",
    r"\bvery helpful\b",
    r"\bloved this\b$",
    r"\bthis was helpful\b$",
]


def clean_comment_line(text: str) -> str:
    value = (text or "").strip()

    value = re.sub(r"^\s*[-*•]+\s*", "", value)
    value = re.sub(r"^\s*\d+[.)]\s*", "", value)
    value = re.sub(r"^\s*[A-Za-z][.)]\s*", "", value)

    value = value.replace('"', "")
    value = value.replace("'", "")
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

    for pattern in BANNED_PATTERNS:
        if re.search(pattern, lowered):
            return True

    return False


def looks_too_generic(text: str) -> bool:
    lowered = text.lower().strip()

    for pattern in GENERIC_PATTERNS:
        if re.search(pattern, lowered):
            return True

    return False


def is_reasonable_length(text: str) -> bool:
    words = text.split()
    return 8 <= len(words) <= 28


def normalize_comments(raw_comments: List[str]) -> List[str]:
    cleaned: List[str] = []
    seen = set()

    for comment in raw_comments:
        value = clean_comment_line(comment)

        if not value:
            continue

        if looks_spammy(value):
            continue

        if looks_too_generic(value):
            continue

        if not is_reasonable_length(value):
            continue

        key = value.lower()
        if key in seen:
            continue

        seen.add(key)
        cleaned.append(value)

    return cleaned[:3]


def extract_comments_from_text(text: str) -> List[str]:
    if not text:
        return []

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return []

    filtered_lines = []
    for line in lines:
        cleaned = clean_comment_line(line)
        if not cleaned:
            continue
        filtered_lines.append(cleaned)

    comments = normalize_comments(filtered_lines)
    if len(comments) >= 3:
        return comments[:3]

    sentence_chunks = re.split(r"\n+|(?<=[.!?])\s+(?=[A-Z])", text)
    filtered_chunks = []

    for chunk in sentence_chunks:
        cleaned = clean_comment_line(chunk)
        if not cleaned:
            continue
        filtered_chunks.append(cleaned)

    sentence_comments = normalize_comments(filtered_chunks)
    return sentence_comments[:3]


def shorten_description(description: str, max_len: int = 500) -> str:
    if not description:
        return ""
    clean = re.sub(r"\s+", " ", description).strip()
    return clean[:max_len]


def build_comment_prompt(video) -> str:
    title = (video.title or "").strip()
    description = shorten_description(video.description or "")
    niche = (video.niche or "").strip()

    return f"""
Video title: {title}
Video description: {description}
Channel name: {video.channel_name}
Niche: {niche}

Write 3 natural YouTube comments for this video.

Important:
- Make each comment specific to this video
- Use real cues from the title or description
- Mention a concrete detail, topic, step, theme, or style when possible
- Do not sound generic
- Do not write a heading or intro sentence
- Do not say "here are 3 comments"
- Never directly ask for anything in return
- Make the comments feel like they came from a real viewer
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

    chat_urls = [
        f"{settings.OLLAMA_BASE_URL}/api/chat",
        f"{settings.OLLAMA_BASE_URL}/v1/chat/completions",
    ]

    last_error = None

    with httpx.Client(timeout=30.0) as client:
        for url in chat_urls:
            try:
                response = client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()

                text = ""

                if "message" in data and isinstance(data["message"], dict):
                    text = data["message"].get("content", "") or ""
                elif "choices" in data and data["choices"]:
                    choice = data["choices"][0]
                    if "message" in choice and isinstance(choice["message"], dict):
                        text = choice["message"].get("content", "") or ""

                comments = extract_comments_from_text(text)
                if comments:
                    return comments

            except Exception as exc:
                last_error = exc
                continue

    if last_error:
        print(f"Ollama generation failed: {last_error}")

    return []


def generate_rule_based_comments(video) -> List[str]:
    title = (video.title or "").lower()
    description = (video.description or "").lower()
    niche = (video.niche or "").lower()

    specific = []

    if "meal prep" in title or "meal prep" in description:
        specific.extend([
            "The way you broke the meal prep into manageable steps made it feel much less overwhelming",
            "I liked that this meal prep felt realistic instead of trying to make everything look perfect",
        ])

    if "fastapi" in title or "fastapi" in description:
        specific.extend([
            "The way you walked through the FastAPI setup made the whole thing feel much easier to follow",
            "I liked that you made the FastAPI part feel practical instead of overexplaining every detail",
        ])

    if "python" in title or "python" in description:
        specific.extend([
            "This made the Python side feel much more approachable than most videos I run into",
            "I liked that the Python explanation stayed clear without slowing everything down too much",
        ])

    if "travel" in niche or "vlog" in title or "vlog" in description:
        specific.extend([
            "The way you put this vlog together made the whole thing feel really easy to stay with",
            "I liked that this travel video felt immersive without trying too hard to force the vibe 🌍",
        ])

    if "makeup" in title or "skincare" in title or niche == "beauty":
        specific.extend([
            "I liked how you kept this look approachable instead of making it feel impossible to recreate",
            "The way you explained each part of this routine made it feel much more wearable and realistic",
        ])

    if "workout" in title or niche == "fitness":
        specific.extend([
            "I liked that this workout felt realistic enough to actually come back to more than once",
            "The way you explained this made it feel motivating without becoming overwhelming 👏",
        ])

    if "recipe" in title or niche == "food":
        specific.extend([
            "The way you showed each step made this recipe feel a lot more doable than I expected",
            "I liked that this recipe felt practical and still satisfying to watch the whole way through",
        ])

    pool = specific + RULE_BASED_COMMENTS
    random.shuffle(pool)

    return normalize_comments(pool)[:3]


def ensure_three_comments(comments: List[str], video) -> List[str]:
    final_comments = normalize_comments(comments)

    if len(final_comments) >= 3:
        return final_comments[:3]

    fallback = generate_rule_based_comments(video)
    seen = {c.lower() for c in final_comments}

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