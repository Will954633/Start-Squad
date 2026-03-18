"""
React to human workout posts with persona responses.
Triggered when a human logs a workout — 1-3 personas react, staggered 2-15 min apart.
"""

import random
import asyncio

from logger import log
from db.connection import async_session
from db.queries.posts import get_channel_history
from db.queries.personas import get_all_personas
from db.queries.users import get_user_by_telegram_id
from db.models import TeamGroup, User
from sqlalchemy import select
from bot.app import get_persona_bot
from personas.manager import generate_and_send_reaction


async def schedule_reactions_to_post(chat_id: int, user_telegram_id: int):
    """
    Schedule 1-3 persona reactions to the human's most recent post.
    Called after a human logs a workout.
    """
    async with async_session() as session:
        user = await get_user_by_telegram_id(session, user_telegram_id)
        if not user:
            return

        result = await session.execute(
            select(TeamGroup).where(TeamGroup.user_id == user.id)
        )
        team_group = result.scalar_one_or_none()
        if not team_group:
            return

        # Get the most recent posts to find human's latest
        history = await get_channel_history(session, team_group.id, 1)
        human_posts = [p for p in history if p.author_type == "human"]
        if not human_posts:
            return

        trigger_post = human_posts[-1]

        # Pick 1-3 random personas to react
        personas = await get_all_personas(session)
        num_reactors = random.choices([1, 2, 3], weights=[0.3, 0.5, 0.2], k=1)[0]
        reactors = random.sample(personas, min(num_reactors, len(personas)))

        # First reactor: quick (2-5 min), rest: 5-15 min
        for i, persona in enumerate(reactors):
            if i == 0:
                delay = random.randint(120, 300)  # 2-5 min
            else:
                delay = random.randint(300, 900)  # 5-15 min

            asyncio.create_task(
                _delayed_reaction(team_group.id, persona.id, trigger_post.id, delay)
            )
            log.info(
                f"Scheduled reaction from {persona.slug} in {delay}s "
                f"to post {trigger_post.id}"
            )


async def _delayed_reaction(
    team_group_id: int, persona_id: int, post_id: int, delay: int
):
    """Send a reaction after a delay."""
    await asyncio.sleep(delay)

    async with async_session() as session:
        from db.models import Persona, TeamGroup, WorkoutPost
        from sqlalchemy import select

        persona = (await session.execute(
            select(Persona).where(Persona.id == persona_id)
        )).scalar_one_or_none()

        team_group = (await session.execute(
            select(TeamGroup).where(TeamGroup.id == team_group_id)
        )).scalar_one_or_none()

        trigger_post = (await session.execute(
            select(WorkoutPost).where(WorkoutPost.id == post_id)
        )).scalar_one_or_none()

        if not all([persona, team_group, trigger_post]):
            return

        bot = get_persona_bot(persona.slug)
        if not bot:
            return

        await generate_and_send_reaction(
            session, persona, team_group, trigger_post, bot
        )
