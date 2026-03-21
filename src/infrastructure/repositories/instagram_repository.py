from datetime import datetime
from uuid import UUID
from sqlalchemy import select, func, desc
from src.infrastructure.repositories.base import BaseRepository


class InstagramRepository(BaseRepository):

    async def get_user_by_ig_id(self, ig_id: str) -> dict | None:
        t = self._t("ig_users")
        stmt = select(t.c.id, t.c.ig_id, t.c.username, t.c.name).where(t.c.ig_id == ig_id)
        result = await self._session.execute(stmt)
        row = result.mappings().first()
        return dict(row) if row else None

    async def get_latest_snapshot(self, user_id: UUID) -> dict | None:
        t = self._t("ig_user_snapshots")
        stmt = (
            select(t.c.followers_count, t.c.follows_count, t.c.media_count)
            .where(t.c.user_id == user_id)
            .order_by(desc(t.c.date))
            .limit(1)
        )
        result = await self._session.execute(stmt)
        row = result.mappings().first()
        return dict(row) if row else None

    async def get_total_engagement(self, user_id: UUID) -> tuple[int, int]:
        t = self._t("ig_posts")
        stmt = select(
            func.coalesce(func.sum(t.c.like_count), 0).label("total_likes"),
            func.coalesce(func.sum(t.c.comments_count), 0).label("total_comments"),
        ).where(t.c.user_id == user_id)
        result = await self._session.execute(stmt)
        row = result.one()
        return int(row.total_likes), int(row.total_comments)

    async def get_post_count(self, user_id: UUID) -> int:
        t = self._t("ig_posts")
        stmt = select(func.count()).select_from(t).where(t.c.user_id == user_id)
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def get_follower_snapshots(
        self, user_id: UUID, date_from: datetime | None, date_to: datetime | None
    ) -> list[dict]:
        t = self._t("ig_user_snapshots")
        stmt = (
            select(t.c.date, t.c.followers_count, t.c.follows_count, t.c.media_count)
            .where(t.c.user_id == user_id)
        )
        if date_from:
            stmt = stmt.where(t.c.date >= date_from)
        if date_to:
            stmt = stmt.where(t.c.date <= date_to)
        stmt = stmt.order_by(t.c.date)
        result = await self._session.execute(stmt)
        return [dict(r) for r in result.mappings().all()]

    async def get_top_posts(
        self, user_id: UUID, date_from: datetime | None, date_to: datetime | None, limit: int = 20
    ) -> list[dict]:
        t = self._t("ig_posts")
        stmt = (
            select(
                t.c.id, t.c.ig_id, t.c.media_type, t.c.caption, t.c.permalink,
                t.c.timestamp, t.c.like_count, t.c.comments_count,
            )
            .where(t.c.user_id == user_id)
        )
        if date_from:
            stmt = stmt.where(t.c.timestamp >= date_from)
        if date_to:
            stmt = stmt.where(t.c.timestamp <= date_to)
        stmt = stmt.order_by(
            desc(func.coalesce(t.c.like_count, 0) + func.coalesce(t.c.comments_count, 0))
        ).limit(limit)
        result = await self._session.execute(stmt)
        return [dict(r) for r in result.mappings().all()]

    async def get_post_insights(self, post_id: UUID) -> dict | None:
        t = self._t("ig_post_insights")
        stmt = (
            select(t.c.reach, t.c.saved, t.c.views, t.c.shares)
            .where(t.c.post_id == post_id)
            .order_by(desc(t.c.date))
            .limit(1)
        )
        result = await self._session.execute(stmt)
        row = result.mappings().first()
        return dict(row) if row else None

    async def get_profile_insights(
        self, user_id: UUID, date_from: datetime | None, date_to: datetime | None
    ) -> list[dict]:
        t = self._t("ig_profile_insights")
        stmt = (
            select(
                t.c.date, t.c.period, t.c.reach, t.c.profile_views, t.c.views,
                t.c.likes, t.c.comments, t.c.shares, t.c.saves, t.c.website_clicks,
                t.c.replies, t.c.reposts,
            )
            .where(t.c.user_id == user_id)
        )
        if date_from:
            stmt = stmt.where(t.c.date >= date_from)
        if date_to:
            stmt = stmt.where(t.c.date <= date_to)
        stmt = stmt.order_by(t.c.date)
        result = await self._session.execute(stmt)
        return [dict(r) for r in result.mappings().all()]
