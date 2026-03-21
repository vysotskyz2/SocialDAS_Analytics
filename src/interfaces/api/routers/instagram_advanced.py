from datetime import datetime
from fastapi import APIRouter, Depends, Query
from dependency_injector.wiring import inject, Provide

from src.interfaces.api.containers import Container
from src.application.services.instagram_advanced import InstagramAdvancedService
from src.infrastructure.schemas.advanced import (
    GrowthResponse, ContentPerformanceResponse, PostingPatternsResponse, TrendsResponse,
)

router = APIRouter(prefix="/api/v1/analytics/instagram", tags=["instagram-advanced"])


@router.get("/{account_id}/growth", response_model=GrowthResponse)
@inject
async def growth(
    account_id: str,
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    projection_days: int = Query(14, ge=1, le=90),
    service: InstagramAdvancedService = Depends(Provide[Container.instagram_advanced_service]),
):
    return await service.get_growth(account_id, date_from, date_to, projection_days)


@router.get("/{account_id}/content-performance", response_model=ContentPerformanceResponse)
@inject
async def content_performance(
    account_id: str,
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    service: InstagramAdvancedService = Depends(Provide[Container.instagram_advanced_service]),
):
    return await service.get_content_performance(account_id, date_from, date_to, limit)


@router.get("/{account_id}/posting-patterns", response_model=PostingPatternsResponse)
@inject
async def posting_patterns(
    account_id: str,
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    service: InstagramAdvancedService = Depends(Provide[Container.instagram_advanced_service]),
):
    return await service.get_posting_patterns(account_id, date_from, date_to)


@router.get("/{account_id}/trends", response_model=TrendsResponse)
@inject
async def trends(
    account_id: str,
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    split_date: datetime | None = Query(None, description="Date to split period-over-period comparison"),
    service: InstagramAdvancedService = Depends(Provide[Container.instagram_advanced_service]),
):
    return await service.get_trends(account_id, date_from, date_to, split_date)
