from datetime import datetime
from fastapi import HTTPException, status
from src.infrastructure.repositories.tiktok_repository import TikTokRepository
from src.infrastructure.schemas.tiktok import (
    TTOverview, TTFollowersResponse, TTFollowersPoint,
    TTVideosResponse, TTVideoItem, TTEngagementResponse, TTEngagementPoint,
)

class TikTokAnalyticsService:

    def __init__(self, repository: TikTokRepository) -> None:
        self._repo = repository

    async def get_overview(self, account_id: str) -> TTOverview:
        user = await self._repo.get_user_by_open_id(account_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="TikTok account not found")
        count, total_views, total_likes, total_comments, total_shares = await self._repo.get_video_stats(user["id"])
        followers = user["follower_count"]
        following = user["following_count"]
        profile_likes = user["likes_count"]
        video_count = user["video_count"]
        if not followers or followers == 0:
            snapshots = await self._repo.get_follower_snapshots(user["id"], None, None)
            if snapshots:
                followers = snapshots[-1]["follower_count"]
                following = snapshots[-1]["following_count"]
                if not profile_likes: profile_likes = snapshots[-1]["likes_count"]
                if not video_count: video_count = snapshots[-1]["video_count"]
        if not profile_likes or profile_likes == 0:
            profile_likes = total_likes
        if not video_count or video_count == 0:
            video_count = count
        avg_views = round(total_views / video_count, 2) if video_count > 0 else (round(total_views / count, 2) if count > 0 else None)
        avg_er = None
        if total_views > 0:
            avg_er = round((total_likes + total_comments + total_shares) / total_views * 100, 4)
        return TTOverview(
            account_id=account_id,
            display_name=user["display_name"],
            followers=followers,
            following=following,
            total_likes=profile_likes,
            total_comments=total_comments,
            total_views=total_views,
            video_count=video_count,
            avg_views=avg_views,
            avg_engagement_rate=avg_er,
        )

    async def get_followers(
        self, account_id: str, date_from: datetime | None, date_to: datetime | None
    ) -> TTFollowersResponse:
        user = await self._repo.get_user_by_open_id(account_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="TikTok account not found")
        snapshots = await self._repo.get_follower_snapshots(user["id"], date_from, date_to)
        data = [
            TTFollowersPoint(
                date=s["date"],
                follower_count=s["follower_count"],
                following_count=s["following_count"],
                likes_count=s["likes_count"],
                video_count=s["video_count"],
            )
            for s in snapshots
        ]
        return TTFollowersResponse(account_id=account_id, data=data)

    async def get_videos(
        self, account_id: str, date_from: datetime | None, date_to: datetime | None, limit: int = 20
    ) -> TTVideosResponse:
        user = await self._repo.get_user_by_open_id(account_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="TikTok account not found")
        videos = await self._repo.get_top_videos(user["id"], date_from, date_to, limit)
        count, *_ = await self._repo.get_video_stats(user["id"])
        items = []
        for v in videos:
            views = v["view_count"] or 0
            engagement = (v["like_count"] or 0) + (v["comment_count"] or 0) + (v["share_count"] or 0)
            er = round(engagement / views * 100, 4) if views > 0 else None
            items.append(TTVideoItem(
                tt_video_id=v["tt_video_id"],
                title=v["title"],
                duration=v["duration"],
                share_url=v["share_url"],
                create_time=v["create_time"],
                like_count=v["like_count"],
                comment_count=v["comment_count"],
                share_count=v["share_count"],
                view_count=v["view_count"],
                engagement_rate=er,
            ))
        return TTVideosResponse(account_id=account_id, total_videos=count, data=items)

    async def get_engagement(
        self, account_id: str, date_from: datetime | None, date_to: datetime | None
    ) -> TTEngagementResponse:
        user = await self._repo.get_user_by_open_id(account_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="TikTok account not found")
        trends = await self._repo.get_video_snapshot_trends(user["id"], date_from, date_to)
        data = []
        for t in trends:
            total_views = t["total_views"] or 0
            total_interactions = (t["total_likes"] or 0) + (t["total_comments"] or 0) + (t["total_shares"] or 0)
            er = round(total_interactions / total_views * 100, 4) if total_views > 0 else None
            data.append(TTEngagementPoint(
                date=t["date"],
                total_likes=t["total_likes"],
                total_comments=t["total_comments"],
                total_shares=t["total_shares"],
                total_views=t["total_views"],
                engagement_rate=er,
            ))
        return TTEngagementResponse(account_id=account_id, data=data)
