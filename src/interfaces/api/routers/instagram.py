from datetime import datetime
from fastapi import APIRouter, Depends, Query
from dependency_injector.wiring import inject, Provide
from src.interfaces.api.containers import Container
from src.application.services.instagram_service import InstagramAnalyticsService
from src.infrastructure.schemas.instagram import (
    IGOverview, IGFollowersResponse, IGPostsResponse, IGEngagementResponse,
)

router = APIRouter(prefix="/api/v1/analytics/instagram", tags=["instagram"])


@router.get("/{account_id}/overview", response_model=IGOverview)
@inject
async def overview(
    account_id: str,
    service: InstagramAnalyticsService = Depends(Provide[Container.instagram_service]),
):
    return await service.get_overview(account_id)


@router.get("/{account_id}/followers", response_model=IGFollowersResponse)
@inject
async def followers(
    account_id: str,
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    service: InstagramAnalyticsService = Depends(Provide[Container.instagram_service]),
):
    return await service.get_followers(account_id, date_from, date_to)


@router.get("/{account_id}/posts", response_model=IGPostsResponse)
@inject
async def posts(
    account_id: str,
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    service: InstagramAnalyticsService = Depends(Provide[Container.instagram_service]),
):
    return await service.get_posts(account_id, date_from, date_to, limit)


@router.get("/{account_id}/engagement", response_model=IGEngagementResponse)
@inject
async def engagement(
    account_id: str,
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    service: InstagramAnalyticsService = Depends(Provide[Container.instagram_service]),
):
    return await service.get_engagement(account_id, date_from, date_to)
