from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from src.settings import settings

engine = create_async_engine(settings.db.url, echo=False, pool_pre_ping=True)

async_session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
    engine,
    expire_on_commit=False,
    class_=AsyncSession,
)

metadata = MetaData()


async def reflect_tables() -> None:
    """Reflect all tables from the Processor database at startup."""
    async with engine.begin() as conn:
        await conn.run_sync(metadata.reflect)
