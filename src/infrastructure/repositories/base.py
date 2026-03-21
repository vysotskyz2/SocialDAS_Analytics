from sqlalchemy.ext.asyncio import AsyncSession
from src.infrastructure.models.base import metadata


class BaseRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @staticmethod
    def _t(name: str):
        return metadata.tables[name]
