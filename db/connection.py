from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from config import Config
from logger import log


def _get_async_url(url: str) -> str:
    """Convert a DATABASE_URL to an async-compatible one.

    Railway provides postgresql://... but we need postgresql+asyncpg://...
    Local dev uses sqlite+aiosqlite:///...
    """
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    return url


db_url = _get_async_url(Config.DATABASE_URL)
log.info(f"Database URL scheme: {db_url.split('://')[0]}")

engine = create_async_engine(
    db_url,
    echo=not Config.is_production(),
    pool_pre_ping=True,
)

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_session() -> AsyncSession:
    async with async_session() as session:
        yield session


async def init_db():
    from db.models import Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    log.info("Database tables created")


async def close_db():
    await engine.dispose()
    log.info("Database connection closed")
