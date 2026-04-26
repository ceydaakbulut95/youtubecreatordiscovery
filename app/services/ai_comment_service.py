import random
import re
from typing import List

import httpx

from app.core.config import settings


SYSTEM_PROMPT = """
You write natural YouTube comments that feel like they were written by a real person.

Main goals:
- Sound warm, believable, and human
- Leave a memorable impression on the creator
- Indirectly increase the chance that the creator notices the commenter and visit your channel too
- Make the creator feel seen, appreciated, and a little curious
- Use some emojis in a natural way when it fits.

Rules:
- Write exactly 3 comment options
- Each comment should feel like it was written by someone who actually watched the video
- Comments should be supportive, natural, and slightly personal
- Keep comments between 14 and 30 words
- No bullet points
- No dashes
- No numbering
- No quotation marks
- No hashtags
- Use 1 or 3 emoji per comment
- Not every comment should include an emoji
- Avoid robotic phrases
- Avoid generic phrases like:
  great content
  valuable content
  thanks for sharing
  keep it up
  amazing video
- Do not ask for follow back, subscribe back, support back, or channel check
- Do not self-promote but the comments can still make the creator curious about the commenter in a subtle way
- Make the 3 comments clearly different from each other and avoid repeating the same phrases across comments
- 1 comment can be friendly, the other one can be curiosity-driven, the other one can be more focused on praising the creator's style for example
- Some comments can mention the creator's style, pacing, clarity, or channel vibe in a subtle way
- Try to understand the description and title to get a sense of the creator's approach and what they might appreciate hearing in the comments
- Sometimes highlight that you like this video and that it made you want to check out more of their channel
- Don't forget that we comment to create a connection with the creator, so it`s not just about sounding natural, but also making the creator feel a certain way that increases the chance they check out the commenter's channel
- We want to grow our channel by building genuine connections with creatorers, so the comments should be crafted with that in mind
"""


RULE_BASED_COMMENTS = [
    "This was such an easy watch, and now I’m genuinely curious what else is on your channel 👀",
    "You have a really natural way of explaining things, which honestly makes people want to keep watching",
    "I found this video randomly and ended up staying way longer than I expected",
    "There’s something really watchable about your style, it doesn’t feel forced at all",
    "This actually felt super clear without dragging, which is rarer than people think",
    "This was my first video from your channel and it honestly made a really strong impression",
    "You made this feel approachable in a way that keeps people from clicking away 👏",
    "I can already tell this is the kind of channel people end up coming back to",
    "This had such a nice balance of useful and easy to follow, which is not easy to do",
    "I clicked for the topic but ended up noticing how easy your videos are to stay with",
    "This felt a lot more genuine than most videos in this niche, and that really stands out",
    "You explain things in a way that makes the whole channel feel worth exploring a bit more",
    "This was honestly a really solid first video to land on from your channel",
    "You have one of those styles that makes people want to check one more upload before leaving",
    "This was way more engaging than I expected, and I mean that in the best way",
]


BANNED_PATTERNS = [
    r"\bgreat content\b",
    r"\bvaluable content\b",
    r"\bkeep it up\b",
    r"\bamazing video\b",
    r"\bsupport me too\b",
    r"\bsub back\b",
    r"\bsubscribe back\b",
    r"\bcheck out my page\b",
    r"\bvisit my channel\b",
    r"\bvisit my page\b",
    r"\bfollow me\b",
    r"\bcome to my channel\b",
    r"\bcome check\b",
]


INTRO_PATTERNS = [
    r"^here are\b",
    r"^here's\b",
    r"^below are\b",
    r"^these are\b",
    r"^youtube comments for\b",
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

    if len(value) >= 2:
        if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
            value = value[1:-1].strip()

    value = value.replace("“", "").replace("”", "").replace("‘", "").replace("’", "")
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


def is_reasonable_length(text: str) -> bool:
    words = text.split()
    return 8 <= len(words) <= 24


def normalize_comments(raw_comments: List[str]) -> List[str]:
    cleaned: List[str] = []
    seen = set()

    for comment in raw_comments:
        value = clean_comment_line(comment)

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


def build_comment_prompt(video) -> str:
    return f"""
Video title: {video.title}
Channel name: {video.channel_name}
Niche: {video.niche}

Write 3 natural YouTube comments for this video.

The comments should:
- feel like they came from someone who genuinely watched
- feel warm and believable
- make the creator feel noticed
- subtly increase the chance that the creator becomes curious about the commenter
- never directly ask for anything in return
- avoid sounding polished, corporate, or fake
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
    niche = (video.niche or "").lower()

    niche_specific = []

    if niche == "food":
        niche_specific = [
            "This made the whole thing feel a lot less intimidating, and now I kind of want to try it myself 😄",
            "You somehow made this feel both simple and satisfying to watch, which is a really nice combo",
            "This was such a good first video to land on from a food channel honestly",
        ]
    elif niche == "fitness":
        niche_specific = [
            "I like that this felt realistic and not overly intense, which makes it way easier to come back to",
            "This was actually motivating without feeling pushy, and that makes a big difference 👏",
            "You made this feel approachable in a way that keeps people from giving up early",
        ]
    elif niche == "beauty":
        niche_specific = [
            "This looked polished without feeling impossible to recreate, which I really appreciated",
            "You explain things in such a calm and natural way, it makes the whole channel feel inviting",
            "This was honestly a really nice first impression of your channel ✨",
        ]
    elif niche == "coding":
        niche_specific = [
            "This was clearer than most coding videos I run into, and that really stands out fast",
            "You have a way of explaining this stuff that makes people want to keep watching",
            "I clicked for the topic but stayed because the pacing actually made sense 👏",
        ]
    elif niche == "travel":
        niche_specific = [
            "This had such an easy vibe to watch, and now I want to see where else you’ve been",
            "There’s something about your style that makes the whole channel feel worth exploring a bit more 🌍",
            "This was such a strong first travel video to come across from your channel",
        ]

    title_specific = []
    if "beginner" in title:
        title_specific.append("This really felt like something beginners could stay with without getting lost halfway through")
    if "easy" in title or "simple" in title:
        title_specific.append("I liked that this stayed simple without making it feel watered down")
    if "tutorial" in title:
        title_specific.append("This actually felt like a tutorial someone would finish, which says a lot")

    pool = RULE_BASED_COMMENTS + niche_specific + title_specific
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