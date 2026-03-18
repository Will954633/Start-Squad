"""
Midnight job: plans the entire next day.
Assigns posting times, moods, rest days for all personas in all active groups.
"""

import random
from datetime import datetime, timedelta

from logger import log
from db.connection import async_session
from db.queries.scheduling import get_active_team_groups, create_scheduled_job
from db.queries.personas import get_all_personas
from personas.variance import assign_daily_mood, is_rest_day
from personas.definitions import PERSONAS


def _random_time_in_window(base_date: datetime, window: dict) -> datetime:
    """Generate a random time within a posting window, avoiding exact hours."""
    start_minutes = window["start_hour"] * 60 + window.get("start_min", 0)
    end_minutes = window["end_hour"] * 60 + window.get("end_min", 0)

    # Random minute within window, avoiding :00
    rand_minute = random.randint(start_minutes, end_minutes)
    # Add jitter to avoid posting on the exact minute
    jitter = random.randint(1, 14)
    rand_minute = min(rand_minute + jitter, end_minutes)

    return base_date.replace(
        hour=rand_minute // 60,
        minute=rand_minute % 60,
        second=random.randint(0, 59),
    )


async def plan_next_day():
    """Plan all persona posts for tomorrow."""
    tomorrow = datetime.utcnow().replace(
        hour=0, minute=0, second=0, microsecond=0
    ) + timedelta(days=1)

    log.info(f"Planning posts for {tomorrow.date()}")

    # Look up persona definitions for off-day settings
    persona_defs = {p["slug"]: p for p in PERSONAS}

    async with async_session() as session:
        groups = await get_active_team_groups(session)
        personas = await get_all_personas(session)

        jobs_created = 0
        for group in groups:
            for persona in personas:
                p_def = persona_defs.get(persona.slug, {})
                off_freq = p_def.get("off_day_frequency", 7)

                # Check if rest day
                if is_rest_day(off_freq):
                    log.debug(f"[{persona.slug}] Rest day for group {group.id}")
                    continue

                # Schedule primary window post
                windows = persona.posting_window
                primary = windows.get("primary")
                if primary:
                    post_time = _random_time_in_window(tomorrow, primary)
                    await create_scheduled_job(
                        session,
                        team_group_id=group.id,
                        persona_id=persona.id,
                        job_type="workout_post",
                        scheduled_for=post_time,
                    )
                    jobs_created += 1

                # 40% chance of secondary window post (if exists)
                secondary = windows.get("secondary")
                if secondary and random.random() < 0.4:
                    post_time = _random_time_in_window(tomorrow, secondary)
                    await create_scheduled_job(
                        session,
                        team_group_id=group.id,
                        persona_id=persona.id,
                        job_type="workout_post",
                        scheduled_for=post_time,
                    )
                    jobs_created += 1

        log.info(f"Planned {jobs_created} persona posts for {tomorrow.date()}")
