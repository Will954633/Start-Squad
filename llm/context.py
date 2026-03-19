"""Builds context windows for LLM prompts from database records."""

from datetime import datetime
from db.models import WorkoutPost, Persona, User


def format_post_for_context(post: WorkoutPost, personas: dict[int, str]) -> str:
    """Format a single post for inclusion in chat history context."""
    if post.author_type == "human":
        author = "You (human)"
    else:
        author = personas.get(post.author_persona_id, "Team member")

    exercise_info = ""
    if post.exercise_type and post.reps:
        exercise_info = f" [{post.exercise_type}: {post.reps} reps]"

    time_str = post.posted_at.strftime("%I:%M%p").lstrip("0").lower()
    return f"[{time_str}] {author}: {post.message_text}{exercise_info}"


def build_chat_history(
    posts: list[WorkoutPost],
    persona_names: dict[int, str],
) -> str:
    """Format a list of posts into a readable chat history string."""
    if not posts:
        return "(No recent messages)"

    lines = [format_post_for_context(p, persona_names) for p in posts]
    return "\n".join(lines)


def get_time_period(hour: int) -> str:
    """Return human-readable time period."""
    if hour < 6:
        return "early morning"
    elif hour < 9:
        return "morning"
    elif hour < 12:
        return "late morning"
    elif hour < 14:
        return "lunchtime"
    elif hour < 17:
        return "afternoon"
    elif hour < 20:
        return "evening"
    else:
        return "night"


# All persona metadata
_PERSONA_DATA = {
    # Male team
    "damo": {"age": 32, "suburb": "Nerang", "job": "electrician"},
    "sam":  {"age": 29, "suburb": "Southport", "job": "physio student at Griffith Uni"},
    "jake": {"age": 24, "suburb": "Palm Beach", "job": "barista / Bond Uni student"},
    "ryan": {"age": 30, "suburb": "Mermaid Beach", "job": "marketing manager (WFH)"},
    "tom":  {"age": 36, "suburb": "Mudgeeraba", "job": "project manager, dad of two"},
    # Female team
    "tash":  {"age": 28, "suburb": "Burleigh Heads", "job": "graphic designer (WFH)"},
    "bree":  {"age": 31, "suburb": "Broadbeach", "job": "real estate agent"},
    "priya": {"age": 27, "suburb": "Southport", "job": "physio student at Griffith Uni"},
    "jess":  {"age": 23, "suburb": "Labrador", "job": "barista / beauty therapy student"},
    "mel":   {"age": 35, "suburb": "Robina", "job": "accountant, mum of a 3-year-old"},
}


def get_persona_age(slug: str) -> int:
    return _PERSONA_DATA.get(slug, {}).get("age", 28)


def get_persona_suburb(slug: str) -> str:
    return _PERSONA_DATA.get(slug, {}).get("suburb", "Gold Coast")


def get_persona_occupation(slug: str) -> str:
    data = _PERSONA_DATA.get(slug, {})
    return f"{data.get('job', '')}, {data.get('suburb', '')}"
