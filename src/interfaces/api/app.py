from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, status, HTTPException, Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from dependency_injector.wiring import inject, Provide

from src.infrastructure.logging_config import setup_logging
from src.infrastructure.models.base import async_session_factory, reflect_tables
from src.interfaces.api.containers import Container, db_session_context
from src.interfaces.api.routers import instagram, tiktok, youtube
from src.interfaces.api.routers import instagram_advanced, tiktok_advanced, youtube_advanced


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    await reflect_tables()

    container = Container()
    container.wire()
    await container.init_resources()

    yield

    await container.shutdown_resources()


app = FastAPI(lifespan=lifespan)


@app.middleware("http")
async def db_session_middleware(request: Request, call_next):
    async with async_session_factory() as session:
        token = db_session_context.set(session)
        try:
            response = await call_next(request)
            return response
        finally:
            db_session_context.reset(token)


@app.get("/health", status_code=status.HTTP_200_OK)
@inject
async def health_check(db: AsyncSession = Depends(Provide[Container.db_session])):
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE)


app.include_router(instagram.router)
app.include_router(tiktok.router)
app.include_router(youtube.router)
app.include_router(instagram_advanced.router)
app.include_router(tiktok_advanced.router)
app.include_router(youtube_advanced.router)
