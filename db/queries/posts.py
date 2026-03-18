from datetime import datetime, timedelta
from sqlalchemy import select, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from db.models import WorkoutPost, ReactionMessage


async def create_workout_post(
    session: AsyncSession,
    team_group_id: int,
    author_type: str,
    message_text: str,
    exercise_type: str | None = None,
    reps: int | None = None,
    sets: int | None = None,
    author_user_id: int | None = None,
    author_persona_id: int | None = None,
    telegram_message_id: int | None = None,
    mood: str | None = None,
) -> WorkoutPost:
    post = WorkoutPost(
        team_group_id=team_group_id,
        author_type=author_type,
        author_user_id=author_user_id,
        author_persona_id=author_persona_id,
        exercise_type=exercise_type,
        reps=reps,
        sets=sets,
        message_text=message_text,
        telegram_message_id=telegram_message_id,
        mood=mood,
    )
    session.add(post)
    await session.commit()
    await session.refresh(post)
    return post


async def get_last_n_posts_by_persona(
    session: AsyncSession, team_group_id: int, persona_id: int, n: int = 8
) -> list[WorkoutPost]:
    result = await session.execute(
        select(WorkoutPost)
        .where(
            and_(
                WorkoutPost.team_group_id == team_group_id,
                WorkoutPost.author_persona_id == persona_id,
            )
        )
        .order_by(desc(WorkoutPost.posted_at))
        .limit(n)
    )
    return list(reversed(result.scalars().all()))


async def get_channel_history(
    session: AsyncSession, team_group_id: int, days: int = 2
) -> list[WorkoutPost]:
    cutoff = datetime.utcnow() - timedelta(days=days)
    result = await session.execute(
        select(WorkoutPost)
        .where(
            and_(
                WorkoutPost.team_group_id == team_group_id,
                WorkoutPost.posted_at >= cutoff,
            )
        )
        .order_by(WorkoutPost.posted_at)
    )
    return list(result.scalars().all())


async def get_human_posts_today(
    session: AsyncSession, team_group_id: int, user_id: int
) -> list[WorkoutPost]:
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    result = await session.execute(
        select(WorkoutPost)
        .where(
            and_(
                WorkoutPost.team_group_id == team_group_id,
                WorkoutPost.author_user_id == user_id,
                WorkoutPost.author_type == "human",
                WorkoutPost.posted_at >= today_start,
            )
        )
    )
    return list(result.scalars().all())


async def create_reaction(
    session: AsyncSession,
    team_group_id: int,
    persona_id: int,
    message_text: str,
    in_reply_to_post_id: int | None = None,
    telegram_message_id: int | None = None,
) -> ReactionMessage:
    reaction = ReactionMessage(
        team_group_id=team_group_id,
        persona_id=persona_id,
        in_reply_to_post_id=in_reply_to_post_id,
        message_text=message_text,
        telegram_message_id=telegram_message_id,
    )
    session.add(reaction)
    await session.commit()
    await session.refresh(reaction)
    return reaction
