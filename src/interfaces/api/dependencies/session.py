from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from src.infrastructure.models.base import async_session_factory


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()
