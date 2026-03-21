from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, status, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.logging_config import setup_logging
from src.interfaces.api.dependencies.session import get_db
from src.interfaces.api.routers import instagram, tiktok, youtube
from src.interfaces.api.routers import instagram_advanced, tiktok_advanced, youtube_advanced


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    from src.infrastructure.models.base import reflect_tables
    await reflect_tables()
    yield


app = FastAPI(lifespan=lifespan)

app.include_router(instagram.router)
app.include_router(tiktok.router)
app.include_router(youtube.router)
app.include_router(instagram_advanced.router)
app.include_router(tiktok_advanced.router)
app.include_router(youtube_advanced.router)


@app.get("/health", status_code=status.HTTP_200_OK)
async def health_check(db: AsyncSession = Depends(get_db)):
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE)
