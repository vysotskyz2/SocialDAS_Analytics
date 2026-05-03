
from datetime import timezone, timedelta

def _to_msk_naive(dt):
    if dt and dt.tzinfo:
        return dt.astimezone(timezone.utc).replace(tzinfo=None) + timedelta(hours=3)
    return dt
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
                v.outerjoin(
                    vs,
                    (v.c.id == vs.c.video_id)
                ).outerjoin(
                    latest,
                    (vs.c.video_id == latest.c.video_id) & (vs.c.date == latest.c.max_date)
                )
            )
            .where(
                (v.c.channel_id == channel_id) &
                ((vs.c.date == latest.c.max_date) | (vs.c.video_id == None))
            )
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
        date_from = _to_msk_naive(date_from)
        if date_from:
            stmt = stmt.where(t.c.date >= date_from)
        date_to = _to_msk_naive(date_to)
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
                v.c.yt_video_id, v.c.title, v.c.description, v.c.published_at, v.c.duration, v.c.thumbnail_url,
                vs.c.view_count, vs.c.like_count, vs.c.comment_count,
            )
            .select_from(
                v.join(vs, v.c.id == vs.c.video_id)
                .join(latest, (vs.c.video_id == latest.c.video_id) & (vs.c.date == latest.c.max_date))
            )
            .where(v.c.channel_id == channel_id)
        )
        date_from = _to_msk_naive(date_from)
        if date_from:
            stmt = stmt.where(v.c.published_at >= date_from)
        date_to = _to_msk_naive(date_to)
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
        day_trunc = func.date_trunc("day", vs.c.date).label("day")
        create_day = func.date_trunc("day", v.c.published_at).label("create_day")
        daily_max = (
            select(
                vs.c.video_id,
                day_trunc,
                create_day,
                func.max(vs.c.view_count).label("max_views"),
                func.max(vs.c.like_count).label("max_likes"),
                func.max(vs.c.comment_count).label("max_comments"),
            )
            .select_from(vs.join(v, vs.c.video_id == v.c.id))
            .where(v.c.channel_id == channel_id)
            .group_by(vs.c.video_id, day_trunc, create_day)
        ).subquery("daily_max")
        prev_views = func.lag(daily_max.c.max_views).over(partition_by=daily_max.c.video_id, order_by=daily_max.c.day)
        prev_likes = func.lag(daily_max.c.max_likes).over(partition_by=daily_max.c.video_id, order_by=daily_max.c.day)
        prev_comments = func.lag(daily_max.c.max_comments).over(partition_by=daily_max.c.video_id, order_by=daily_max.c.day)
        days_diff = func.extract('epoch', daily_max.c.day - daily_max.c.create_day) / 86400
        from sqlalchemy import case
        is_new_video = days_diff <= 3
        deltas = (
            select(
                daily_max.c.day,
                case((prev_views != None, daily_max.c.max_views - prev_views), (is_new_video, daily_max.c.max_views), else_=0).label("delta_views"),
                case((prev_likes != None, daily_max.c.max_likes - prev_likes), (is_new_video, daily_max.c.max_likes), else_=0).label("delta_likes"),
                case((prev_comments != None, daily_max.c.max_comments - prev_comments), (is_new_video, daily_max.c.max_comments), else_=0).label("delta_comments"),
            )
        ).subquery("deltas")
        stmt = (
            select(
                deltas.c.day.label("date"),
                func.sum(deltas.c.delta_views).label("total_views"),
                func.sum(deltas.c.delta_likes).label("total_likes"),
                func.sum(deltas.c.delta_comments).label("total_comments"),
            )
            .group_by(deltas.c.day)
            .order_by(deltas.c.day)
        )
        date_from = _to_msk_naive(date_from)
        if date_from:
            stmt = stmt.where(deltas.c.day >= date_from)
        date_to = _to_msk_naive(date_to)
        if date_to:
            stmt = stmt.where(deltas.c.day <= date_to)
        result = await self._session.execute(stmt)
        return [dict(r) for r in result.mappings().all()]