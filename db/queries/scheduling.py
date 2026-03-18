from datetime import datetime
from sqlalchemy import select, and_, update
from sqlalchemy.ext.asyncio import AsyncSession
from db.models import ScheduledJob, TeamGroup


async def create_scheduled_job(
    session: AsyncSession,
    team_group_id: int,
    job_type: str,
    scheduled_for: datetime,
    persona_id: int | None = None,
) -> ScheduledJob:
    job = ScheduledJob(
        team_group_id=team_group_id,
        persona_id=persona_id,
        job_type=job_type,
        scheduled_for=scheduled_for,
    )
    session.add(job)
    await session.commit()
    await session.refresh(job)
    return job


async def get_pending_jobs(
    session: AsyncSession, before: datetime
) -> list[ScheduledJob]:
    result = await session.execute(
        select(ScheduledJob)
        .where(
            and_(
                ScheduledJob.status == "pending",
                ScheduledJob.scheduled_for <= before,
            )
        )
        .order_by(ScheduledJob.scheduled_for)
    )
    return list(result.scalars().all())


async def mark_job_executed(session: AsyncSession, job_id: int):
    await session.execute(
        update(ScheduledJob)
        .where(ScheduledJob.id == job_id)
        .values(status="executed", executed_at=datetime.utcnow())
    )
    await session.commit()


async def mark_job_failed(session: AsyncSession, job_id: int):
    await session.execute(
        update(ScheduledJob)
        .where(ScheduledJob.id == job_id)
        .values(status="failed", executed_at=datetime.utcnow())
    )
    await session.commit()


async def get_active_team_groups(session: AsyncSession) -> list[TeamGroup]:
    result = await session.execute(
        select(TeamGroup).where(TeamGroup.is_active == True)
    )
    return list(result.scalars().all())
