
from datetime import timezone, timedelta

def _to_msk_naive(dt):
    if dt and dt.tzinfo:
        return dt.astimezone(timezone.utc).replace(tzinfo=None) + timedelta(hours=3)
    return dt
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

    async def get_total_views(self, user_id: UUID) -> int:
        pi = self._t("ig_post_insights")
        p = self._t("ig_posts")
        latest = (
            select(pi.c.post_id, func.max(pi.c.date).label("max_date"))
            .group_by(pi.c.post_id)
            .subquery("latest")
        )
        stmt = (
            select(func.coalesce(func.sum(pi.c.views), 0))
            .select_from(p.join(pi, p.c.id == pi.c.post_id).join(latest, (pi.c.post_id == latest.c.post_id) & (pi.c.date == latest.c.max_date)))
            .where(p.c.user_id == user_id)
        )
        result = await self._session.execute(stmt)
        return int(result.scalar_one())

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
        date_from = _to_msk_naive(date_from)
        if date_from:
            stmt = stmt.where(t.c.date >= date_from)
        date_to = _to_msk_naive(date_to)
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
                t.c.thumbnail_url, t.c.media_url,
            )
            .where(t.c.user_id == user_id)
        )
        date_from = _to_msk_naive(date_from)
        if date_from:
            stmt = stmt.where(t.c.timestamp >= date_from)
        date_to = _to_msk_naive(date_to)
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
        day_trunc = func.date_trunc("day", t.c.date).label("date")
        stmt = (
            select(
                day_trunc,
                t.c.period,
                func.max(t.c.reach).label("reach"),
                func.max(t.c.profile_views).label("profile_views"),
                func.max(t.c.views).label("views"),
                func.max(t.c.likes).label("likes"),
                func.max(t.c.comments).label("comments"),
                func.max(t.c.shares).label("shares"),
                func.max(t.c.saves).label("saves"),
                func.max(t.c.website_clicks).label("website_clicks"),
                func.max(t.c.replies).label("replies"),
                func.max(t.c.reposts).label("reposts"),
            )
            .where(t.c.user_id == user_id)
        )
        date_from = _to_msk_naive(date_from)
        if date_from:
            stmt = stmt.where(t.c.date >= date_from)
        date_to = _to_msk_naive(date_to)
        if date_to:
            stmt = stmt.where(t.c.date <= date_to)
        stmt = stmt.group_by(day_trunc, t.c.period).order_by(day_trunc)
        result = await self._session.execute(stmt)
        return [dict(r) for r in result.mappings().all()]
    async def get_post_trends(
        self, user_id: UUID, date_from: datetime | None, date_to: datetime | None
    ) -> list[dict]:
        t = self._t("ig_posts")
        date_trunc = func.date_trunc("day", t.c.timestamp).label("date")
        stmt = (
            select(
                date_trunc,
                func.sum(t.c.like_count).label("likes"),
                func.sum(t.c.comments_count).label("comments"),
                func.count(t.c.id).label("posts_count"),
            )
            .where(t.c.user_id == user_id)
        )
        date_from = _to_msk_naive(date_from)
        if date_from:
            stmt = stmt.where(t.c.timestamp >= date_from)
        date_to = _to_msk_naive(date_to)
        if date_to:
            stmt = stmt.where(t.c.timestamp <= date_to)
        stmt = stmt.group_by(date_trunc).order_by(date_trunc)
        result = await self._session.execute(stmt)
        return [dict(r) for r in result.mappings().all()]