from datetime import datetime
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.interfaces.api.dependencies.session import get_db
from src.application.services.instagram_service import InstagramAnalyticsService
from src.infrastructure.repositories.instagram_repository import InstagramRepository
from src.infrastructure.schemas.instagram import (
    IGOverview, IGFollowersResponse, IGPostsResponse, IGEngagementResponse,
)

router = APIRouter(prefix="/api/v1/reports/instagram", tags=["instagram"])


def _get_service(session: AsyncSession = Depends(get_db)) -> InstagramAnalyticsService:
    return InstagramAnalyticsService(repository=InstagramRepository(session))


@router.get("/{account_id}/overview", response_model=IGOverview)
async def overview(
    account_id: str,
    service: InstagramAnalyticsService = Depends(_get_service),
):
    return await service.get_overview(account_id)


@router.get("/{account_id}/followers", response_model=IGFollowersResponse)
async def followers(
    account_id: str,
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    service: InstagramAnalyticsService = Depends(_get_service),
):
    return await service.get_followers(account_id, date_from, date_to)


@router.get("/{account_id}/posts", response_model=IGPostsResponse)
async def posts(
    account_id: str,
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    service: InstagramAnalyticsService = Depends(_get_service),
):
    return await service.get_posts(account_id, date_from, date_to, limit)


@router.get("/{account_id}/engagement", response_model=IGEngagementResponse)
async def engagement(
    account_id: str,
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    service: InstagramAnalyticsService = Depends(_get_service),
):
    return await service.get_engagement(account_id, date_from, date_to)
