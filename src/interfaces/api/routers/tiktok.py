from datetime import datetime
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.interfaces.api.dependencies.session import get_db
from src.application.services.tiktok_service import TikTokAnalyticsService
from src.infrastructure.repositories.tiktok_repository import TikTokRepository
from src.infrastructure.schemas.tiktok import (
    TTOverview, TTFollowersResponse, TTVideosResponse, TTEngagementResponse,
)

router = APIRouter(prefix="/api/v1/reports/tiktok", tags=["tiktok"])


def _get_service(session: AsyncSession = Depends(get_db)) -> TikTokAnalyticsService:
    return TikTokAnalyticsService(repository=TikTokRepository(session))


@router.get("/{account_id}/overview", response_model=TTOverview)
async def overview(
    account_id: str,
    service: TikTokAnalyticsService = Depends(_get_service),
):
    return await service.get_overview(account_id)


@router.get("/{account_id}/followers", response_model=TTFollowersResponse)
async def followers(
    account_id: str,
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    service: TikTokAnalyticsService = Depends(_get_service),
):
    return await service.get_followers(account_id, date_from, date_to)


@router.get("/{account_id}/videos", response_model=TTVideosResponse)
async def videos(
    account_id: str,
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    service: TikTokAnalyticsService = Depends(_get_service),
):
    return await service.get_videos(account_id, date_from, date_to, limit)


@router.get("/{account_id}/engagement", response_model=TTEngagementResponse)
async def engagement(
    account_id: str,
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    service: TikTokAnalyticsService = Depends(_get_service),
):
    return await service.get_engagement(account_id, date_from, date_to)
