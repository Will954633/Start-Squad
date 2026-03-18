from datetime import date, timedelta
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from db.models import DailyStat, WorkoutPost


async def get_or_create_daily_stat(
    session: AsyncSession, user_id: int, stat_date: date
) -> DailyStat:
    result = await session.execute(
        select(DailyStat).where(
            and_(DailyStat.user_id == user_id, DailyStat.stat_date == stat_date)
        )
    )
    stat = result.scalar_one_or_none()
    if not stat:
        stat = DailyStat(user_id=user_id, stat_date=stat_date)
        session.add(stat)
        await session.commit()
        await session.refresh(stat)
    return stat


async def update_daily_stat(
    session: AsyncSession,
    user_id: int,
    stat_date: date,
    squats: int = 0,
    pushups: int = 0,
    situps: int = 0,
):
    stat = await get_or_create_daily_stat(session, user_id, stat_date)
    stat.total_squats += squats
    stat.total_pushups += pushups
    stat.total_situps += situps
    stat.workout_count += 1
    stat.completed = True
    await session.commit()


async def get_weekly_stats(
    session: AsyncSession, user_id: int
) -> list[DailyStat]:
    week_ago = date.today() - timedelta(days=7)
    result = await session.execute(
        select(DailyStat)
        .where(and_(DailyStat.user_id == user_id, DailyStat.stat_date >= week_ago))
        .order_by(DailyStat.stat_date)
    )
    return list(result.scalars().all())


async def get_monthly_stats(
    session: AsyncSession, user_id: int
) -> list[DailyStat]:
    month_ago = date.today() - timedelta(days=30)
    result = await session.execute(
        select(DailyStat)
        .where(and_(DailyStat.user_id == user_id, DailyStat.stat_date >= month_ago))
        .order_by(DailyStat.stat_date)
    )
    return list(result.scalars().all())


async def get_current_streak(session: AsyncSession, user_id: int) -> int:
    today = date.today()
    streak = 0
    check_date = today
    while True:
        result = await session.execute(
            select(DailyStat).where(
                and_(
                    DailyStat.user_id == user_id,
                    DailyStat.stat_date == check_date,
                    DailyStat.completed == True,
                )
            )
        )
        if result.scalar_one_or_none():
            streak += 1
            check_date -= timedelta(days=1)
        else:
            break
    return streak
