from datetime import datetime
from fastapi import APIRouter, Depends, Query
from dependency_injector.wiring import inject, Provide
from src.interfaces.api.containers import Container
from src.application.services.youtube_service import YouTubeAnalyticsService
from src.infrastructure.schemas.youtube import (
    YTOverview, YTSubscribersResponse, YTVideosResponse, YTEngagementResponse,
)

router = APIRouter(prefix="/api/v1/analytics/youtube", tags=["youtube"])


@router.get("/{account_id}/overview", response_model=YTOverview)
@inject
async def overview(
    account_id: str,
    service: YouTubeAnalyticsService = Depends(Provide[Container.youtube_service]),
):
    return await service.get_overview(account_id)


@router.get("/{account_id}/subscribers", response_model=YTSubscribersResponse)
@inject
async def subscribers(
    account_id: str,
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    service: YouTubeAnalyticsService = Depends(Provide[Container.youtube_service]),
):
    return await service.get_subscribers(account_id, date_from, date_to)


@router.get("/{account_id}/videos", response_model=YTVideosResponse)
@inject
async def videos(
    account_id: str,
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    service: YouTubeAnalyticsService = Depends(Provide[Container.youtube_service]),
):
    return await service.get_videos(account_id, date_from, date_to, limit)


@router.get("/{account_id}/engagement", response_model=YTEngagementResponse)
@inject
async def engagement(
    account_id: str,
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    service: YouTubeAnalyticsService = Depends(Provide[Container.youtube_service]),
):
    return await service.get_engagement(account_id, date_from, date_to)
