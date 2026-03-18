from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from db.models import User


async def get_user_by_telegram_id(session: AsyncSession, telegram_id: int) -> User | None:
    result = await session.execute(
        select(User).where(User.telegram_id == telegram_id)
    )
    return result.scalar_one_or_none()


async def create_user(
    session: AsyncSession,
    telegram_id: int,
    first_name: str,
    city: str,
    fitness_level: str,
    goals: str = "",
    telegram_username: str | None = None,
    timezone: str = "Australia/Brisbane",
    gender: str = "",
    suburb: str = "",
    pushup_variant: str = "toes",
    situp_variant: str = "full_situps",
) -> User:
    user = User(
        telegram_id=telegram_id,
        telegram_username=telegram_username,
        first_name=first_name,
        gender=gender,
        city=city,
        suburb=suburb,
        fitness_level=fitness_level,
        goals=goals,
        timezone=timezone,
        pushup_variant=pushup_variant,
        situp_variant=situp_variant,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def mark_onboarding_complete(session: AsyncSession, user_id: int):
    await session.execute(
        update(User).where(User.id == user_id).values(onboarding_complete=True)
    )
    await session.commit()


async def get_all_active_users(session: AsyncSession) -> list[User]:
    result = await session.execute(
        select(User).where(User.is_active == True, User.onboarding_complete == True)
    )
    return list(result.scalars().all())
