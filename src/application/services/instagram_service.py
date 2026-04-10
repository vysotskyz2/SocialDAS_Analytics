from datetime import datetime
from fastapi import HTTPException, status
from src.infrastructure.repositories.instagram_repository import InstagramRepository
from src.infrastructure.schemas.instagram import (
    IGOverview, IGFollowersResponse, IGFollowersPoint,
    IGPostsResponse, IGPostItem, IGEngagementResponse, IGEngagementPoint,
)


class InstagramAnalyticsService:

    def __init__(self, repository: InstagramRepository) -> None:
        self._repo = repository

    async def get_overview(self, account_id: str) -> IGOverview:
        user = await self._repo.get_user_by_ig_id(account_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Instagram account not found")
        snapshot = await self._repo.get_latest_snapshot(user["id"])
        total_likes, total_comments = await self._repo.get_total_engagement(user["id"])
        total_views = await self._repo.get_total_views(user["id"])
        followers = user.get("followers_count") or (snapshot["followers_count"] if snapshot else 0)
        following = user.get("follows_count") or (snapshot["follows_count"] if snapshot else 0)
        media_count = user.get("media_count") or (snapshot["media_count"] if snapshot else 0)
        post_count = await self._repo.get_post_count(user["id"])
        avg_views = round(total_views / post_count, 2) if post_count > 0 else 0
        avg_er = None
        if followers and followers > 0:
            if post_count > 0:
                avg_er = round((total_likes + total_comments) / post_count / followers * 100, 4)
        return IGOverview(
            account_id=account_id,
            username=user["username"],
            followers=followers,
            following=following,
            media_count=media_count,
            total_likes=total_likes,
            total_comments=total_comments,
            total_views=total_views,
            avg_views=avg_views,
            avg_engagement_rate=avg_er,
        )

    async def get_followers(
        self, account_id: str, date_from: datetime | None, date_to: datetime | None
    ) -> IGFollowersResponse:
        user = await self._repo.get_user_by_ig_id(account_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Instagram account not found")
        snapshots = await self._repo.get_follower_snapshots(user["id"], date_from, date_to)
        data = [
            IGFollowersPoint(
                date=s["date"],
                followers=s["followers_count"],
                follows=s["follows_count"],
                media_count=s["media_count"],
            )
            for s in snapshots
        ]
        return IGFollowersResponse(account_id=account_id, data=data)

    async def get_posts(
        self, account_id: str, date_from: datetime | None, date_to: datetime | None, limit: int = 20
    ) -> IGPostsResponse:
        user = await self._repo.get_user_by_ig_id(account_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Instagram account not found")
        posts = await self._repo.get_top_posts(user["id"], date_from, date_to, limit)
        items: list[IGPostItem] = []
        for p in posts:
            insight = await self._repo.get_post_insights(p["id"])
            engagement = (p["like_count"] or 0) + (p["comments_count"] or 0)
            items.append(IGPostItem(
                ig_id=p["ig_id"],
                media_type=p["media_type"] if p["media_type"] else None,
                caption=p["caption"][:200] if p["caption"] else None,
                permalink=p["permalink"],
                timestamp=p["timestamp"],
                like_count=p["like_count"],
                comments_count=p["comments_count"],
                engagement=engagement,
                reach=insight["reach"] if insight else None,
                saved=insight["saved"] if insight else None,
                views=insight["views"] if insight else None,
                shares=insight["shares"] if insight else None,
            ))
        post_count = await self._repo.get_post_count(user["id"])
        return IGPostsResponse(account_id=account_id, total_posts=post_count, data=items)

    async def get_engagement(
        self, account_id: str, date_from: datetime | None, date_to: datetime | None
    ) -> IGEngagementResponse:
        user = await self._repo.get_user_by_ig_id(account_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Instagram account not found")
        insights = await self._repo.get_profile_insights(user["id"], date_from, date_to)
        post_trends = await self._repo.get_post_trends(user["id"], date_from, date_to)
        trends_map = {pt["date"].date(): pt for pt in post_trends}
        data = []
        for i in insights:
            dt = i["date"]
            likes = i["likes"] if i["likes"] is not None else trends_map.get(dt.date(), {}).get("likes", 0)
            comments = i["comments"] if i["comments"] is not None else trends_map.get(dt.date(), {}).get("comments", 0)
            reach = i["reach"] or 0
            er = None
            if reach > 0:
                er = round((likes + comments) / reach * 100, 4)
            data.append(IGEngagementPoint(
                date=dt,
                period=i["period"],
                reach=i["reach"],
                profile_views=i["profile_views"],
                views=i["views"],
                likes=likes,
                comments=comments,
                shares=i["shares"],
                saves=i["saves"],
                website_clicks=i["website_clicks"],
                engagement_rate=er
            ))
        if not data and post_trends:
            for pt in post_trends:
                data.append(IGEngagementPoint(
                    date=pt["date"],
                    period="day",
                    reach=0,
                    profile_views=0,
                    views=0,
                    likes=pt["likes"],
                    comments=pt["comments"],
                    shares=0,
                    saves=0,
                    website_clicks=0,
                    engagement_rate=None
                ))
        return IGEngagementResponse(account_id=account_id, data=data)
