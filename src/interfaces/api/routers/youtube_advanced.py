from datetime import datetime
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.interfaces.api.dependencies.session import get_db
from src.application.services.youtube_advanced import YouTubeAdvancedService
from src.infrastructure.repositories.youtube_repository import YouTubeRepository
from src.infrastructure.schemas.advanced import (
    GrowthResponse, ContentPerformanceResponse, PostingPatternsResponse, TrendsResponse,
)

router = APIRouter(prefix="/api/v1/reports/youtube", tags=["youtube-advanced"])


def _get_service(session: AsyncSession = Depends(get_db)) -> YouTubeAdvancedService:
    return YouTubeAdvancedService(repository=YouTubeRepository(session))


@router.get("/{account_id}/growth", response_model=GrowthResponse)
async def growth(
    account_id: str,
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    projection_days: int = Query(14, ge=1, le=90),
    service: YouTubeAdvancedService = Depends(_get_service),
):
    return await service.get_growth(account_id, date_from, date_to, projection_days)


@router.get("/{account_id}/content-performance", response_model=ContentPerformanceResponse)
async def content_performance(
    account_id: str,
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    service: YouTubeAdvancedService = Depends(_get_service),
):
    return await service.get_content_performance(account_id, date_from, date_to, limit)


@router.get("/{account_id}/posting-patterns", response_model=PostingPatternsResponse)
async def posting_patterns(
    account_id: str,
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    service: YouTubeAdvancedService = Depends(_get_service),
):
    return await service.get_posting_patterns(account_id, date_from, date_to)


@router.get("/{account_id}/trends", response_model=TrendsResponse)
async def trends(
    account_id: str,
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    split_date: datetime | None = Query(None, description="Date to split period-over-period comparison"),
    service: YouTubeAdvancedService = Depends(_get_service),
):
    return await service.get_trends(account_id, date_from, date_to, split_date)
