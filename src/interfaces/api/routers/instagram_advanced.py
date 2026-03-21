from datetime import datetime
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.interfaces.api.dependencies.session import get_db
from src.application.services.instagram_advanced import InstagramAdvancedService
from src.infrastructure.repositories.instagram_repository import InstagramRepository
from src.infrastructure.schemas.advanced import (
    GrowthResponse, ContentPerformanceResponse, PostingPatternsResponse, TrendsResponse,
)

router = APIRouter(prefix="/api/v1/reports/instagram", tags=["instagram-advanced"])


def _get_service(session: AsyncSession = Depends(get_db)) -> InstagramAdvancedService:
    return InstagramAdvancedService(repository=InstagramRepository(session))


@router.get("/{account_id}/growth", response_model=GrowthResponse)
async def growth(
    account_id: str,
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    projection_days: int = Query(14, ge=1, le=90),
    service: InstagramAdvancedService = Depends(_get_service),
):
    return await service.get_growth(account_id, date_from, date_to, projection_days)


@router.get("/{account_id}/content-performance", response_model=ContentPerformanceResponse)
async def content_performance(
    account_id: str,
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    service: InstagramAdvancedService = Depends(_get_service),
):
    return await service.get_content_performance(account_id, date_from, date_to, limit)


@router.get("/{account_id}/posting-patterns", response_model=PostingPatternsResponse)
async def posting_patterns(
    account_id: str,
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    service: InstagramAdvancedService = Depends(_get_service),
):
    return await service.get_posting_patterns(account_id, date_from, date_to)


@router.get("/{account_id}/trends", response_model=TrendsResponse)
async def trends(
    account_id: str,
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    split_date: datetime | None = Query(None, description="Date to split period-over-period comparison"),
    service: InstagramAdvancedService = Depends(_get_service),
):
    return await service.get_trends(account_id, date_from, date_to, split_date)
