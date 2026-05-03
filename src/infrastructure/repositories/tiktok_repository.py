
from datetime import timezone, timedelta

def _to_msk_naive(dt):
    if dt and dt.tzinfo:
        return dt.astimezone(timezone.utc).replace(tzinfo=None) + timedelta(hours=3)
    return dt
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
        date_from = _to_msk_naive(date_from)
        if date_from:
            stmt = stmt.where(t.c.create_time >= date_from)
        date_to = _to_msk_naive(date_to)
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
        day_trunc = func.date_trunc("day", vs.c.date).label("day")
        create_day = func.date_trunc("day", v.c.create_time).label("create_day")
        daily_max = (
            select(
                vs.c.video_id,
                day_trunc,
                create_day,
                func.max(vs.c.view_count).label("max_views"),
                func.max(vs.c.like_count).label("max_likes"),
                func.max(vs.c.comment_count).label("max_comments"),
                func.max(vs.c.share_count).label("max_shares"),
            )
            .select_from(vs.join(v, vs.c.video_id == v.c.id))
            .where(v.c.user_id == user_id)
            .group_by(vs.c.video_id, day_trunc, create_day)
        ).subquery("daily_max")
        prev_views = func.lag(daily_max.c.max_views).over(partition_by=daily_max.c.video_id, order_by=daily_max.c.day)
        prev_likes = func.lag(daily_max.c.max_likes).over(partition_by=daily_max.c.video_id, order_by=daily_max.c.day)
        prev_comments = func.lag(daily_max.c.max_comments).over(partition_by=daily_max.c.video_id, order_by=daily_max.c.day)
        prev_shares = func.lag(daily_max.c.max_shares).over(partition_by=daily_max.c.video_id, order_by=daily_max.c.day)
        days_diff = func.extract('epoch', daily_max.c.day - daily_max.c.create_day) / 86400

        from sqlalchemy import case

        is_new_video = days_diff <= 3
        deltas = (
            select(
                daily_max.c.day,
                case((prev_views != None, daily_max.c.max_views - prev_views), (is_new_video, daily_max.c.max_views), else_=0).label("delta_views"),
                case((prev_likes != None, daily_max.c.max_likes - prev_likes), (is_new_video, daily_max.c.max_likes), else_=0).label("delta_likes"),
                case((prev_comments != None, daily_max.c.max_comments - prev_comments), (is_new_video, daily_max.c.max_comments), else_=0).label("delta_comments"),
                case((prev_shares != None, daily_max.c.max_shares - prev_shares), (is_new_video, daily_max.c.max_shares), else_=0).label("delta_shares"),
            )
        ).subquery("deltas")
        stmt = (
            select(
                deltas.c.day.label("date"),
                func.sum(deltas.c.delta_likes).label("total_likes"),
                func.sum(deltas.c.delta_comments).label("total_comments"),
                func.sum(deltas.c.delta_shares).label("total_shares"),
                func.sum(deltas.c.delta_views).label("total_views"),
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