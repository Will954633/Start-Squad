"""Execute pending scheduled persona posts."""

import random
import asyncio
from datetime import datetime

from logger import log
from db.connection import async_session
from db.queries.scheduling import get_pending_jobs, mark_job_executed, mark_job_failed
from db.queries.personas import get_persona_by_slug, get_all_personas, get_calibration
from db.queries.users import get_user_by_telegram_id
from db.models import TeamGroup, User
from sqlalchemy import select
from bot.app import get_persona_bot
from personas.manager import generate_and_send_workout_post, generate_and_send_reaction
from personas.variance import assign_daily_mood


async def execute_pending_posts():
    """Check for and execute any pending scheduled posts."""
    now = datetime.utcnow()

    async with async_session() as session:
        pending = await get_pending_jobs(session, before=now)

        for job in pending:
            if job.job_type != "workout_post":
                continue

            try:
                # Get persona
                persona_result = await session.execute(
                    select(Persona).where(Persona.id == job.persona_id)
                )
                from db.models import Persona
                persona = persona_result.scalar_one_or_none()
                if not persona:
                    await mark_job_failed(session, job.id)
                    continue

                # Get team group and user
                group_result = await session.execute(
                    select(TeamGroup).where(TeamGroup.id == job.team_group_id)
                )
                team_group = group_result.scalar_one_or_none()
                if not team_group:
                    await mark_job_failed(session, job.id)
                    continue

                user_result = await session.execute(
                    select(User).where(User.id == team_group.user_id)
                )
                user = user_result.scalar_one_or_none()
                if not user:
                    await mark_job_failed(session, job.id)
                    continue

                # Get persona bot
                bot = get_persona_bot(persona.slug)
                if not bot:
                    log.warning(f"No bot for persona {persona.slug}")
                    await mark_job_failed(session, job.id)
                    continue

                # Get calibration
                cal = await get_calibration(session, user.id, persona.id)
                adjusted = cal.adjusted_baseline if cal else persona.fitness_baseline

                mood = assign_daily_mood()

                success = await generate_and_send_workout_post(
                    session, persona, team_group, user, bot,
                    mood=mood, adjusted_baseline=adjusted,
                )

                if success:
                    await mark_job_executed(session, job.id)

                    # 30% chance another persona reacts
                    if random.random() < 0.3:
                        asyncio.create_task(
                            _delayed_cross_reaction(team_group, persona, user)
                        )
                else:
                    await mark_job_failed(session, job.id)

            except Exception as e:
                log.error(f"Failed to execute job {job.id}: {e}")
                await mark_job_failed(session, job.id)


async def _delayed_cross_reaction(team_group, posting_persona, user):
    """Another persona reacts to the posting persona's message, after a delay."""
    delay = random.randint(120, 900)  # 2-15 minutes
    await asyncio.sleep(delay)

    async with async_session() as session:
        personas = await get_all_personas(session)
        # Pick a different persona
        candidates = [p for p in personas if p.id != posting_persona.id]
        if not candidates:
            return

        reactor = random.choice(candidates)
        bot = get_persona_bot(reactor.slug)
        if not bot:
            return

        # Get the most recent post by the posting persona
        from db.queries.posts import get_last_n_posts_by_persona
        recent = await get_last_n_posts_by_persona(
            session, team_group.id, posting_persona.id, 1
        )
        if not recent:
            return

        await generate_and_send_reaction(
            session, reactor, team_group, recent[0], bot
        )
