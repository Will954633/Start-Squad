from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from db.models import Persona, UserPersonaCalibration


async def get_all_personas(session: AsyncSession) -> list[Persona]:
    result = await session.execute(
        select(Persona).where(Persona.is_active == True)
    )
    return list(result.scalars().all())


async def get_persona_by_slug(session: AsyncSession, slug: str) -> Persona | None:
    result = await session.execute(
        select(Persona).where(Persona.slug == slug)
    )
    return result.scalar_one_or_none()


async def get_calibration(
    session: AsyncSession, user_id: int, persona_id: int
) -> UserPersonaCalibration | None:
    result = await session.execute(
        select(UserPersonaCalibration).where(
            UserPersonaCalibration.user_id == user_id,
            UserPersonaCalibration.persona_id == persona_id,
        )
    )
    return result.scalar_one_or_none()


async def set_calibration(
    session: AsyncSession,
    user_id: int,
    persona_id: int,
    adjusted_baseline: dict,
    variance_factor: float = 0.15,
):
    cal = await get_calibration(session, user_id, persona_id)
    if cal:
        cal.adjusted_baseline = adjusted_baseline
        cal.variance_factor = variance_factor
    else:
        cal = UserPersonaCalibration(
            user_id=user_id,
            persona_id=persona_id,
            adjusted_baseline=adjusted_baseline,
            variance_factor=variance_factor,
        )
        session.add(cal)
    await session.commit()
