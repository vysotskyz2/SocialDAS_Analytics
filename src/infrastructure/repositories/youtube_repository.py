from datetime import datetime
from uuid import UUID
from sqlalchemy import select, func, desc
from src.infrastructure.repositories.base import BaseRepository


class YouTubeRepository(BaseRepository):

    async def get_channel_by_yt_id(self, yt_channel_id: str) -> dict | None:
        t = self._t("yt_channels")
        stmt = select(t.c.id, t.c.yt_channel_id, t.c.title).where(t.c.yt_channel_id == yt_channel_id)
        result = await self._session.execute(stmt)
        row = result.mappings().first()
        return dict(row) if row else None

    async def get_latest_snapshot(self, channel_id: UUID) -> dict | None:
        t = self._t("yt_channel_snapshots")
        stmt = (
            select(t.c.subscriber_count, t.c.video_count, t.c.view_count)
            .where(t.c.channel_id == channel_id)
            .order_by(desc(t.c.date))
            .limit(1)
        )
        result = await self._session.execute(stmt)
        row = result.mappings().first()
        return dict(row) if row else None

    async def get_video_stats(self, channel_id: UUID) -> tuple[int, int, int, int]:
        vs = self._t("yt_video_snapshots")
        v = self._t("yt_videos")

        latest = (
            select(vs.c.video_id, func.max(vs.c.date).label("max_date"))
            .group_by(vs.c.video_id)
            .subquery("latest")
        )

        stmt = (
            select(
                func.count(func.distinct(v.c.id)).label("cnt"),
                func.coalesce(func.sum(vs.c.view_count), 0).label("total_views"),
                func.coalesce(func.sum(vs.c.like_count), 0).label("total_likes"),
                func.coalesce(func.sum(vs.c.comment_count), 0).label("total_comments"),
            )
            .select_from(
                v.join(vs, v.c.id == vs.c.video_id)
                .join(latest, (vs.c.video_id == latest.c.video_id) & (vs.c.date == latest.c.max_date))
            )
            .where(v.c.channel_id == channel_id)
        )
        result = await self._session.execute(stmt)
        row = result.one()
        return int(row.cnt), int(row.total_views), int(row.total_likes), int(row.total_comments)

    async def get_subscriber_snapshots(
        self, channel_id: UUID, date_from: datetime | None, date_to: datetime | None
    ) -> list[dict]:
        t = self._t("yt_channel_snapshots")
        stmt = (
            select(t.c.date, t.c.subscriber_count, t.c.video_count, t.c.view_count)
            .where(t.c.channel_id == channel_id)
        )
        if date_from:
            stmt = stmt.where(t.c.date >= date_from)
        if date_to:
            stmt = stmt.where(t.c.date <= date_to)
        stmt = stmt.order_by(t.c.date)
        result = await self._session.execute(stmt)
        return [dict(r) for r in result.mappings().all()]

    async def get_top_videos(
        self, channel_id: UUID, date_from: datetime | None, date_to: datetime | None, limit: int = 20
    ) -> list[dict]:
        vs = self._t("yt_video_snapshots")
        v = self._t("yt_videos")

        latest = (
            select(vs.c.video_id, func.max(vs.c.date).label("max_date"))
            .group_by(vs.c.video_id)
            .subquery("latest")
        )

        stmt = (
            select(
                v.c.yt_video_id, v.c.title, v.c.published_at, v.c.duration,
                vs.c.view_count, vs.c.like_count, vs.c.comment_count,
            )
            .select_from(
                v.join(vs, v.c.id == vs.c.video_id)
                .join(latest, (vs.c.video_id == latest.c.video_id) & (vs.c.date == latest.c.max_date))
            )
            .where(v.c.channel_id == channel_id)
        )
        if date_from:
            stmt = stmt.where(v.c.published_at >= date_from)
        if date_to:
            stmt = stmt.where(v.c.published_at <= date_to)
        stmt = stmt.order_by(desc(func.coalesce(vs.c.view_count, 0))).limit(limit)
        result = await self._session.execute(stmt)
        return [dict(r) for r in result.mappings().all()]

    async def get_video_snapshot_trends(
        self, channel_id: UUID, date_from: datetime | None, date_to: datetime | None
    ) -> list[dict]:
        vs = self._t("yt_video_snapshots")
        v = self._t("yt_videos")
        stmt = (
            select(
                vs.c.date,
                func.sum(vs.c.view_count).label("total_views"),
                func.sum(vs.c.like_count).label("total_likes"),
                func.sum(vs.c.comment_count).label("total_comments"),
            )
            .select_from(vs.join(v, vs.c.video_id == v.c.id))
            .where(v.c.channel_id == channel_id)
        )
        if date_from:
            stmt = stmt.where(vs.c.date >= date_from)
        if date_to:
            stmt = stmt.where(vs.c.date <= date_to)
        stmt = stmt.group_by(vs.c.date).order_by(vs.c.date)
        result = await self._session.execute(stmt)
        return [dict(r) for r in result.mappings().all()]
