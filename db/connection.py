from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from config import Config
from logger import log

engine = create_async_engine(
    Config.DATABASE_URL,
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
