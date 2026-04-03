from datetime import datetime
from uuid import UUID
from sqlalchemy import select, func, desc
from src.infrastructure.repositories.base import BaseRepository


class TikTokRepository(BaseRepository):

    async def get_user_by_open_id(self, tt_open_id: str) -> dict | None:
        t = self._t("tt_users")
        stmt = select(
            t.c.id, t.c.tt_open_id, t.c.display_name, t.c.follower_count,
            t.c.following_count, t.c.likes_count, t.c.video_count,
        ).where(t.c.tt_open_id == tt_open_id)
        result = await self._session.execute(stmt)
        row = result.mappings().first()
        return dict(row) if row else None

    async def get_video_stats(self, user_id: UUID) -> tuple[int, int, int, int, int]:
        t = self._t("tt_videos")
        stmt = select(
            func.count().label("cnt"),
            func.coalesce(func.sum(t.c.view_count), 0).label("total_views"),
            func.coalesce(func.sum(t.c.like_count), 0).label("total_likes"),
            func.coalesce(func.sum(t.c.comment_count), 0).label("total_comments"),
            func.coalesce(func.sum(t.c.share_count), 0).label("total_shares"),
        ).where(t.c.user_id == user_id)
        result = await self._session.execute(stmt)
        row = result.one()
        return int(row.cnt), int(row.total_views), int(row.total_likes), int(row.total_comments), int(row.total_shares)

    async def get_follower_snapshots(
        self, user_id: UUID, date_from: datetime | None, date_to: datetime | None
    ) -> list[dict]:
        t = self._t("tt_user_snapshots")
        stmt = (
            select(t.c.date, t.c.follower_count, t.c.following_count, t.c.likes_count, t.c.video_count)
            .where(t.c.user_id == user_id)
        )
        if date_from:
            stmt = stmt.where(t.c.date >= date_from)
        if date_to:
            stmt = stmt.where(t.c.date <= date_to)
        stmt = stmt.order_by(t.c.date)
        result = await self._session.execute(stmt)
        return [dict(r) for r in result.mappings().all()]

    async def get_top_videos(
        self, user_id: UUID, date_from: datetime | None, date_to: datetime | None, limit: int = 20
    ) -> list[dict]:
        t = self._t("tt_videos")
        stmt = (
            select(
                t.c.id, t.c.tt_video_id, t.c.title, t.c.duration, t.c.share_url,
                t.c.create_time, t.c.like_count, t.c.comment_count,
                t.c.share_count, t.c.view_count, t.c.cover_image_url,
            )
            .where(t.c.user_id == user_id)
        )
        if date_from:
            stmt = stmt.where(t.c.create_time >= date_from)
        if date_to:
            stmt = stmt.where(t.c.create_time <= date_to)
        stmt = stmt.order_by(desc(func.coalesce(t.c.view_count, 0))).limit(limit)
        result = await self._session.execute(stmt)
        return [dict(r) for r in result.mappings().all()]

    async def get_video_snapshot_trends(
        self, user_id: UUID, date_from: datetime | None, date_to: datetime | None
    ) -> list[dict]:
        vs = self._t("tt_video_snapshots")
        v = self._t("tt_videos")
        stmt = (
            select(
                vs.c.date,
                func.sum(vs.c.like_count).label("total_likes"),
                func.sum(vs.c.comment_count).label("total_comments"),
                func.sum(vs.c.share_count).label("total_shares"),
                func.sum(vs.c.view_count).label("total_views"),
            )
            .select_from(vs.join(v, vs.c.video_id == v.c.id))
            .where(v.c.user_id == user_id)
        )
        if date_from:
            stmt = stmt.where(vs.c.date >= date_from)
        if date_to:
            stmt = stmt.where(vs.c.date <= date_to)
        stmt = stmt.group_by(vs.c.date).order_by(vs.c.date)
        result = await self._session.execute(stmt)
        return [dict(r) for r in result.mappings().all()]
