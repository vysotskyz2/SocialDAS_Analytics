from datetime import datetime

from fastapi import HTTPException, status

from src.infrastructure.repositories.youtube_repository import YouTubeRepository
from src.infrastructure.schemas.youtube import (
    YTOverview, YTSubscribersResponse, YTSubscribersPoint,
    YTVideosResponse, YTVideoItem, YTEngagementResponse, YTEngagementPoint,
)


class YouTubeAnalyticsService:
    def __init__(self, repository: YouTubeRepository) -> None:
        self._repo = repository

    async def get_overview(self, account_id: str) -> YTOverview:
        channel = await self._repo.get_channel_by_yt_id(account_id)
        if not channel:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="YouTube channel not found")

        snapshot = await self._repo.get_latest_snapshot(channel["id"])
        count, total_views, total_likes, total_comments = await self._repo.get_video_stats(channel["id"])

        avg_views = round(total_views / count, 2) if count > 0 else None
        avg_er = None
        if total_views > 0:
            avg_er = round((total_likes + total_comments) / total_views * 100, 4)

        return YTOverview(
            account_id=account_id,
            title=channel["title"],
            subscribers=snapshot["subscriber_count"] if snapshot else None,
            total_views=snapshot["view_count"] if snapshot else None,
            video_count=count,
            avg_views_per_video=avg_views,
            avg_engagement_rate=avg_er,
        )

    async def get_subscribers(
        self, account_id: str, date_from: datetime | None, date_to: datetime | None
    ) -> YTSubscribersResponse:
        channel = await self._repo.get_channel_by_yt_id(account_id)
        if not channel:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="YouTube channel not found")

        snapshots = await self._repo.get_subscriber_snapshots(channel["id"], date_from, date_to)
        data = [
            YTSubscribersPoint(
                date=s["date"],
                subscriber_count=s["subscriber_count"],
                video_count=s["video_count"],
                view_count=s["view_count"],
            )
            for s in snapshots
        ]
        return YTSubscribersResponse(account_id=account_id, data=data)

    async def get_videos(
        self, account_id: str, date_from: datetime | None, date_to: datetime | None, limit: int = 20
    ) -> YTVideosResponse:
        channel = await self._repo.get_channel_by_yt_id(account_id)
        if not channel:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="YouTube channel not found")

        rows = await self._repo.get_top_videos(channel["id"], date_from, date_to, limit)
        count, *_ = await self._repo.get_video_stats(channel["id"])

        items = []
        for row in rows:
            views = int(row["view_count"] or 0)
            engagement = int(row["like_count"] or 0) + int(row["comment_count"] or 0)
            er = round(engagement / views * 100, 4) if views > 0 else None
            items.append(YTVideoItem(
                yt_video_id=row["yt_video_id"],
                title=row["title"],
                published_at=row["published_at"],
                duration=row["duration"],
                view_count=row["view_count"],
                like_count=row["like_count"],
                comment_count=row["comment_count"],
                engagement_rate=er,
            ))

        return YTVideosResponse(account_id=account_id, total_videos=count, data=items)

    async def get_engagement(
        self, account_id: str, date_from: datetime | None, date_to: datetime | None
    ) -> YTEngagementResponse:
        channel = await self._repo.get_channel_by_yt_id(account_id)
        if not channel:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="YouTube channel not found")

        trends = await self._repo.get_video_snapshot_trends(channel["id"], date_from, date_to)
        data = []
        for t in trends:
            total_views = t["total_views"] or 0
            total_interactions = (t["total_likes"] or 0) + (t["total_comments"] or 0)
            er = round(total_interactions / total_views * 100, 4) if total_views > 0 else None
            data.append(YTEngagementPoint(
                date=t["date"],
                total_views=t["total_views"],
                total_likes=t["total_likes"],
                total_comments=t["total_comments"],
                engagement_rate=er,
            ))

        return YTEngagementResponse(account_id=account_id, data=data)
