"""
Workout reporting handlers.
Supports both commands (/workout squats 30) and natural language parsing.
"""

import re
import asyncio
from datetime import date
from telegram import Update
from telegram.ext import ContextTypes

from logger import log
from db.connection import async_session
from db.queries.users import get_user_by_telegram_id
from db.queries.posts import create_workout_post, get_channel_history
from db.queries.stats import update_daily_stat
from db.models import TeamGroup
from sqlalchemy import select

# Regex patterns for workout parsing
EXERCISE_PATTERNS = {
    "squats": re.compile(r"(\d+)\s*(?:squats?|sq)", re.IGNORECASE),
    "pushups": re.compile(r"(\d+)\s*(?:push[\s-]?ups?|pu)", re.IGNORECASE),
    "situps": re.compile(r"(\d+)\s*(?:sit[\s-]?ups?|su|crunches?)", re.IGNORECASE),
}

# General number pattern for commands like /workout squats 30
COMMAND_PATTERN = re.compile(
    r"(squats?|push[\s-]?ups?|sit[\s-]?ups?|crunches?)\s+(\d+)(?:\s+(\d+))?",
    re.IGNORECASE,
)


def normalize_exercise(name: str) -> str:
    """Normalize exercise name to standard form."""
    name = name.lower().replace("-", "").replace(" ", "")
    if name.startswith("squat"):
        return "squats"
    elif name.startswith("push"):
        return "pushups"
    elif name.startswith("sit") or name.startswith("crunch"):
        return "situps"
    return name


def parse_workout_text(text: str) -> dict:
    """
    Parse workout from natural language.
    Returns dict like {"squats": 30, "pushups": 15} or empty dict.
    """
    results = {}
    for exercise, pattern in EXERCISE_PATTERNS.items():
        match = pattern.search(text)
        if match:
            results[exercise] = int(match.group(1))
    return results


async def workout_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /workout and /log commands."""
    if not context.args:
        await update.message.reply_text(
            "Log your workout like this:\n"
            "/workout squats 30\n"
            "/workout pushups 20 3  (20 reps, 3 sets)\n\n"
            "Or just type naturally:\n"
            "\"Did 30 squats and 15 pushups today!\""
        )
        return

    text = " ".join(context.args)
    match = COMMAND_PATTERN.search(text)

    if not match:
        # Try natural language parse
        parsed = parse_workout_text(text)
        if parsed:
            await _log_parsed_workout(update, parsed)
            return
        await update.message.reply_text(
            "Couldn't parse that. Try: /workout squats 30"
        )
        return

    exercise = normalize_exercise(match.group(1))
    reps = int(match.group(2))
    sets = int(match.group(3)) if match.group(3) else 1

    await _log_workout(update, exercise, reps, sets)


async def workout_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle natural language workout messages in groups."""
    text = update.message.text
    parsed = parse_workout_text(text)

    if not parsed:
        return  # Not a workout message, ignore

    await _log_parsed_workout(update, parsed)


async def _log_parsed_workout(update: Update, parsed: dict):
    """Log a parsed multi-exercise workout."""
    for exercise, reps in parsed.items():
        await _log_workout(update, exercise, reps, 1, quiet=len(parsed) > 1)

    exercises = ", ".join(f"{reps} {ex}" for ex, reps in parsed.items())
    await update.message.reply_text(f"Logged: {exercises}. Keep it up! 💪")

    # Trigger persona reactions
    asyncio.create_task(_trigger_reactions(update))


async def _log_workout(
    update: Update, exercise: str, reps: int, sets: int = 1, quiet: bool = False
):
    """Log a single exercise to the database."""
    async with async_session() as session:
        user = await get_user_by_telegram_id(session, update.effective_user.id)
        if not user:
            if not quiet:
                await update.message.reply_text(
                    "You haven't set up yet! Use /start first."
                )
            return

        # Find team group
        result = await session.execute(
            select(TeamGroup).where(TeamGroup.user_id == user.id)
        )
        team_group = result.scalar_one_or_none()

        group_id = team_group.id if team_group else None

        if group_id:
            await create_workout_post(
                session,
                team_group_id=group_id,
                author_type="human",
                message_text=update.message.text,
                exercise_type=exercise,
                reps=reps,
                sets=sets,
                author_user_id=user.id,
                telegram_message_id=update.message.message_id,
            )

        # Update daily stats
        total_reps = reps * sets
        kwargs = {exercise: total_reps}
        await update_daily_stat(session, user.id, date.today(), **kwargs)

    if not quiet:
        sets_text = f" x {sets} sets" if sets > 1 else ""
        await update.message.reply_text(
            f"Logged: {reps} {exercise}{sets_text}. Nice work! 💪"
        )


async def _trigger_reactions(update: Update):
    """Schedule persona reactions to human workout posts."""
    from scheduler.jobs.reactions import schedule_reactions_to_post
    # Small delay before first reaction
    await asyncio.sleep(2)
    try:
        await schedule_reactions_to_post(
            update.effective_chat.id,
            update.effective_user.id,
        )
    except Exception as e:
        log.error(f"Failed to trigger reactions: {e}")
