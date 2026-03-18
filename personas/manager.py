"""
Core persona engine: builds context, calls LLM, validates messages, sends to Telegram.
This is the heart of Start Squad.
"""

import re
from datetime import datetime
from telegram import Bot
from sqlalchemy.ext.asyncio import AsyncSession

from config import Config
from logger import log
from llm.client import generate_message
from llm.prompts import SYSTEM_PROMPT, WORKOUT_POST_PROMPT, REACTION_PROMPT, NUDGE_PROMPT
from llm.context import (
    build_chat_history, get_time_period, get_persona_age, get_persona_occupation,
)
from db.models import Persona, User, TeamGroup
from db.queries.posts import (
    get_last_n_posts_by_persona, get_channel_history,
    create_workout_post, create_reaction, get_human_posts_today,
)
from db.queries.stats import get_current_streak
from personas.variance import generate_workout_numbers, assign_daily_mood, random_sets

# Banned phrases that break immersion
BANNED_PHRASES = [
    "as an ai", "i'm a bot", "i'm not real", "language model",
    "i don't actually", "i can't really", "virtual", "artificial",
    "programmed", "generated", "algorithm", "simulate",
]


def validate_message(message: str, persona_display_name: str) -> bool:
    """Reject messages that break immersion."""
    lower = message.lower()
    for phrase in BANNED_PHRASES:
        if phrase in lower:
            log.warning(f"Rejected message containing '{phrase}': {message[:50]}...")
            return False
    if len(message) > Config.MAX_MESSAGE_LENGTH:
        log.warning(f"Message too long ({len(message)} chars)")
        return False
    if message.startswith(persona_display_name):
        log.warning("Message starts with persona name")
        return False
    return True


async def generate_and_send_workout_post(
    session: AsyncSession,
    persona: Persona,
    team_group: TeamGroup,
    user: User,
    persona_bot: Bot,
    mood: str | None = None,
    adjusted_baseline: dict | None = None,
) -> bool:
    """
    Generate a workout post for a persona and send it to the group.
    Returns True on success.
    """
    if mood is None:
        mood = assign_daily_mood()

    if adjusted_baseline is None:
        adjusted_baseline = persona.fitness_baseline

    # Generate workout numbers
    workout = generate_workout_numbers(
        adjusted_baseline, mood,
        persona.fitness_baseline.get("variance_factor", 0.15),
    )
    sets = random_sets(mood)

    # Build exercise summary
    exercise_parts = []
    for exercise, reps in workout.items():
        exercise_parts.append(f"{reps} {exercise}")
    exercise_summary = f"{', '.join(exercise_parts)} x {sets} sets"

    # Get persona's last 8 posts
    last_posts = await get_last_n_posts_by_persona(session, team_group.id, persona.id, 8)
    persona_names = await _get_persona_names(session)
    last_8_text = build_chat_history(last_posts, persona_names)

    # Get last 2 days of channel history
    history = await get_channel_history(session, team_group.id, 2)
    history_text = build_chat_history(history, persona_names)

    # Get human's last workout info
    human_posts = await get_human_posts_today(session, team_group.id, user.id)
    human_last = human_posts[-1].message_text if human_posts else "No workout yet today"
    streak = await get_current_streak(session, user.id)

    now = datetime.utcnow()
    prompt = WORKOUT_POST_PROMPT.format(
        persona_name=persona.display_name,
        persona_age=get_persona_age(persona.slug),
        city=user.city,
        persona_occupation=get_persona_occupation(persona.slug),
        persona_personality=persona.personality,
        persona_backstory=persona.bio,
        persona_emoji_style=persona.emoji_style,
        persona_slang_notes=persona.slang_notes,
        persona_motivation_style=persona.motivation_style,
        day_of_week=now.strftime("%A"),
        date=now.strftime("%d %B %Y"),
        time_period=get_time_period(now.hour),
        current_time=now.strftime("%I:%M%p").lstrip("0").lower(),
        mood=mood,
        exercise_summary=exercise_summary,
        rest_day_note="",
        last_8_messages=last_8_text,
        channel_history_2_days=history_text,
        human_name=user.first_name,
        human_fitness_level=user.fitness_level,
        human_last_workout=human_last,
        human_streak=streak,
    )

    # Generate message (with up to 3 attempts for validation)
    message = None
    for _ in range(3):
        result = await generate_message(SYSTEM_PROMPT, prompt)
        if result and validate_message(result, persona.display_name):
            message = result
            break
        log.warning("Message failed validation, retrying...")

    if not message:
        log.error(f"Failed to generate valid message for {persona.slug}")
        return False

    # Send to Telegram
    try:
        sent = await persona_bot.send_message(
            chat_id=team_group.telegram_chat_id,
            text=message,
        )
        # Store in database
        # Pick the primary exercise for the record
        primary_exercise = max(workout, key=workout.get)
        await create_workout_post(
            session,
            team_group_id=team_group.id,
            author_type="persona",
            message_text=message,
            exercise_type=primary_exercise,
            reps=workout[primary_exercise],
            sets=sets,
            author_persona_id=persona.id,
            telegram_message_id=sent.message_id,
            mood=mood,
        )
        log.info(f"[{persona.slug}] Posted workout to group {team_group.id}: {message[:60]}...")
        return True

    except Exception as e:
        log.error(f"Failed to send message for {persona.slug}: {e}")
        return False


async def generate_and_send_reaction(
    session: AsyncSession,
    persona: Persona,
    team_group: TeamGroup,
    trigger_post: object,
    persona_bot: Bot,
    persona_names: dict | None = None,
) -> bool:
    """Generate a reaction to someone's post and send it."""
    if persona_names is None:
        persona_names = await _get_persona_names(session)

    # Get recent chat for context
    history = await get_channel_history(session, team_group.id, 1)
    recent_text = build_chat_history(history[-10:], persona_names)

    # Determine post author name
    if trigger_post.author_type == "human":
        post_author = "the human"
    else:
        post_author = persona_names.get(trigger_post.author_persona_id, "a teammate")

    prompt = REACTION_PROMPT.format(
        persona_name=persona.display_name,
        persona_personality=persona.personality,
        persona_emoji_style=persona.emoji_style,
        persona_slang_notes=persona.slang_notes,
        persona_motivation_style=persona.motivation_style,
        post_author_name=post_author,
        post_text=trigger_post.message_text,
        post_exercise=trigger_post.exercise_type or "workout",
        post_reps=trigger_post.reps or "?",
        recent_chat=recent_text,
    )

    message = await generate_message(SYSTEM_PROMPT, prompt, max_tokens=80)
    if not message or not validate_message(message, persona.display_name):
        return False

    try:
        sent = await persona_bot.send_message(
            chat_id=team_group.telegram_chat_id,
            text=message,
            reply_to_message_id=trigger_post.telegram_message_id,
        )
        await create_reaction(
            session,
            team_group_id=team_group.id,
            persona_id=persona.id,
            message_text=message,
            in_reply_to_post_id=trigger_post.id,
            telegram_message_id=sent.message_id,
        )
        log.info(f"[{persona.slug}] Reacted: {message[:60]}...")
        return True
    except Exception as e:
        log.error(f"Failed to send reaction for {persona.slug}: {e}")
        return False


async def generate_and_send_nudge(
    session: AsyncSession,
    persona: Persona,
    team_group: TeamGroup,
    user: User,
    persona_bot: Bot,
) -> bool:
    """Generate an encouraging nudge for inactive human."""
    persona_names = await _get_persona_names(session)
    history = await get_channel_history(session, team_group.id, 1)
    recent_text = build_chat_history(history[-10:], persona_names)
    streak = await get_current_streak(session, user.id)

    now = datetime.utcnow()
    prompt = NUDGE_PROMPT.format(
        persona_name=persona.display_name,
        persona_personality=persona.personality,
        persona_emoji_style=persona.emoji_style,
        persona_slang_notes=persona.slang_notes,
        persona_motivation_style=persona.motivation_style,
        human_name=user.first_name,
        current_time=now.strftime("%I:%M%p").lstrip("0").lower(),
        days_since_last=0,  # Will be calculated properly
        streak=streak,
        fitness_level=user.fitness_level,
        recent_chat=recent_text,
    )

    message = await generate_message(SYSTEM_PROMPT, prompt, max_tokens=100)
    if not message or not validate_message(message, persona.display_name):
        return False

    try:
        await persona_bot.send_message(
            chat_id=team_group.telegram_chat_id,
            text=message,
        )
        log.info(f"[{persona.slug}] Nudged {user.first_name}: {message[:60]}...")
        return True
    except Exception as e:
        log.error(f"Failed to send nudge for {persona.slug}: {e}")
        return False


async def _get_persona_names(session: AsyncSession) -> dict[int, str]:
    """Get mapping of persona_id -> display_name."""
    from db.queries.personas import get_all_personas
    personas = await get_all_personas(session)
    return {p.id: p.display_name for p in personas}
