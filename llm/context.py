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


def get_persona_age(slug: str) -> int:
    """Return persona age from slug."""
    ages = {"mia": 27, "damo": 32, "priya": 29, "jake": 24, "lena": 35}
    return ages.get(slug, 28)


def get_persona_occupation(slug: str) -> str:
    """Return persona occupation from slug."""
    jobs = {
        "mia": "graphic designer (WFH)",
        "damo": "electrician",
        "priya": "physiotherapy student",
        "jake": "barista / uni student",
        "lena": "accountant, mum of a 3-year-old",
    }
    return jobs.get(slug, "")
