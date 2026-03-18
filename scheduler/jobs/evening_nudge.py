"""
Evening nudge — check if human worked out today.
6pm: gentle check from one persona
8pm: more insistent check from a competitive/cheerleader persona
"""

import random
from datetime import date

from logger import log
from db.connection import async_session
from db.queries.users import get_all_active_users
from db.queries.posts import get_human_posts_today
from db.queries.personas import get_all_personas
from db.queries.scheduling import get_active_team_groups
from db.models import TeamGroup
from sqlalchemy import select
from bot.app import get_persona_bot
from personas.manager import generate_and_send_nudge


# Personas more likely to nudge, by motivation style
NUDGE_WEIGHTS = {
    "cheerleader": 3,
    "competitive": 3,
    "joker": 2,
    "realist": 2,
    "coach": 1,
}


async def check_evening_nudge(is_second_check: bool = False):
    """Check all active users and nudge those who haven't worked out."""
    log.info(f"Evening nudge check (second={is_second_check})")

    async with async_session() as session:
        users = await get_all_active_users(session)

        for user in users:
            # Find their team group
            result = await session.execute(
                select(TeamGroup).where(
                    TeamGroup.user_id == user.id,
                    TeamGroup.is_active == True,
                )
            )
            team_group = result.scalar_one_or_none()
            if not team_group:
                continue

            # Check if they posted today
            today_posts = await get_human_posts_today(
                session, team_group.id, user.id
            )
            if today_posts:
                continue  # Already worked out, no nudge needed

            # Select persona(s) to nudge
            personas = await get_all_personas(session)
            if not personas:
                continue

            # Weighted selection
            weights = [
                NUDGE_WEIGHTS.get(p.motivation_style, 1)
                for p in personas
            ]

            # First check: 1 persona nudges
            # Second check: 2 personas nudge
            num_nudgers = 2 if is_second_check else 1
            selected = random.choices(personas, weights=weights, k=num_nudgers)
            # Remove duplicates
            seen = set()
            unique_selected = []
            for p in selected:
                if p.id not in seen:
                    seen.add(p.id)
                    unique_selected.append(p)

            for persona in unique_selected:
                bot = get_persona_bot(persona.slug)
                if not bot:
                    continue

                await generate_and_send_nudge(
                    session, persona, team_group, user, bot
                )
