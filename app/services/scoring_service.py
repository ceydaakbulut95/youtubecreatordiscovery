def normalize_comment_count(count: int) -> float:
    
    if count < 20:
        return 0.2
    elif count < 200:
        return 1.0
    elif count < 500:
        return 0.7
    else:
        return 0.3


def normalize_recency(days: int) -> float:

    if days <= 3:
        return 1.0
    elif days <= 7:
        return 0.8
    elif days <= 30:
        return 0.5
    else:
        return 0.2


def calculate_engagement_score(
    reply_ratio: float,
    comment_count: int,
    days_since_upload: int
) -> float:

    comment_score = normalize_comment_count(comment_count)
    recency_score = normalize_recency(days_since_upload)

    score = (
        (reply_ratio * 0.6)
        + (comment_score * 0.2)
        + (recency_score * 0.2)
    )

    return round(score, 2)