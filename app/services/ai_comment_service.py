import httpx

from app.core.config import settings
from app.schemas.video import VideoCandidate


def _fallback_comment(video: VideoCandidate, style: str) -> str:
    title_lower = video.title.lower()
    description_lower = video.description.lower()

    if style == "friendly":
        if "pasta" in title_lower:
            return "This looks so easy and comforting. Have you ever tried this with whole wheat pasta?"
        if "dinner" in title_lower or "dinner" in description_lower:
            return "I like how simple and realistic this feels for everyday cooking. Do you usually prep these meals in advance?"
        return f"This was really enjoyable to watch. What inspired you to make this {video.niche} video?"

    if style == "curious":
        if "pasta" in title_lower:
            return "This looks great. Would this work well with a lighter sauce too?"
        if "chicken" in title_lower:
            return "This looks really practical for weeknights. What would you usually serve this with?"
        return f"I liked this a lot. What made you choose this version of the recipe?"

    if style == "creator":
        if "pasta" in title_lower:
            return "Love how simple and clear this is. I’ve been trying to make my own food content more practical like this too."
        if "dinner" in title_lower or "dinner" in description_lower:
            return "This feels super approachable and well put together. I know how much thought goes into making content like this."
        return "Really liked how you put this together. I’ve been trying to improve my own content lately too."

    return f"I liked this video a lot. What inspired you to make it?"


def _build_messages(video: VideoCandidate, style: str) -> list[dict]:
    style_instruction = {
        "friendly": "Write in a warm, supportive, natural way.",
        "curious": "Write in a curious, engaging way and naturally ask a question.",
        "creator": "Write like a fellow small creator. Lightly imply that you also create content, but do not promote yourself.",
    }.get(style, "Write naturally and briefly.")

    system_prompt = f"""
You write natural YouTube comments for small creators interacting with each other.

Rules:
- Sound like a real human, not a bot
- Be friendly, supportive, and natural
- Keep it short (1-2 sentences)
- Mention something specific from the video
- Do NOT directly promote your channel
- Do NOT ask for subscriptions
- Avoid spammy phrases like "sub back", "check my channel", "support me"
- Make the creator more likely to respond or check the profile naturally

Additional style rule:
{style_instruction}

Output only the comment text.
""".strip()

    user_prompt = f"""
Video niche: {video.niche}
Video title: {video.title}
Video description: {video.description}
Channel name: {video.channel_name}

Write one YouTube comment in the "{style}" style.
""".strip()

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


def _generate_with_ollama(video: VideoCandidate, style: str) -> str:
    payload = {
        "model": settings.OLLAMA_MODEL,
        "messages": _build_messages(video, style),
        "stream": False,
    }

    response = httpx.post(
        f"{settings.OLLAMA_BASE_URL}/api/chat",
        json=payload,
        timeout=60.0,
    )
    response.raise_for_status()

    data = response.json()
    content = data.get("message", {}).get("content", "").strip()

    if not content:
        return _fallback_comment(video, style)

    return content


def generate_comments(video: VideoCandidate) -> list[str]:
    styles = ["friendly", "curious", "creator"]
    comments: list[str] = []

    for style in styles:
        if settings.LLM_PROVIDER != "ollama":
            comment = _fallback_comment(video, style)
        else:
            try:
                comment = _generate_with_ollama(video, style)
            except Exception as e:
                print(f"Ollama generation failed for style {style}: {e}")
                comment = _fallback_comment(video, style)

        if comment not in comments:
            comments.append(comment)

    return comments