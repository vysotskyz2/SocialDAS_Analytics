from datetime import datetime
import pandas as pd
from fastapi import HTTPException, status
from src.application.services import analytics_engine as engine
from src.infrastructure.repositories.tiktok_repository import TikTokRepository
from src.infrastructure.schemas.advanced import (
    GrowthResponse, GrowthPoint, RegressionInfo, ProjectionPoint,
    ContentPerformanceResponse, ContentItem, StatsInfo, QuartileInfo,
    PostingPatternsResponse, DayEngagement, HourEngagement, BestTime,
    TrendsResponse, AnomalyItem, CorrelationPair, CorrelationPoint, PeriodComparison, PeriodStats,
)


class TikTokAdvancedService:
    def __init__(self, repository: TikTokRepository) -> None:
        self._repo = repository

    async def _resolve_user(self, account_id: str):
        user = await self._repo.get_user_by_open_id(account_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="TikTok account not found")
        return user

    async def get_growth(
        self, account_id: str, date_from: datetime | None, date_to: datetime | None, projection_days: int = 14
    ) -> GrowthResponse:
        user = await self._resolve_user(account_id)
        snapshots = await self._repo.get_follower_snapshots(user["id"], date_from, date_to)

        records = [{"date": s["date"], "followers": s["follower_count"]} for s in snapshots]
        df = engine.build_time_series(records, "date", "followers")

        if df.empty:
            return GrowthResponse(
                account_id=account_id, metric="followers",
                regression=RegressionInfo(slope=None, intercept=None, r_squared=None, direction="insufficient_data"),
                projections=[], data=[],
            )

        growth = engine.compute_growth_rates(df["followers"])
        sma7 = engine.sma(df["followers"], 7)
        sma30 = engine.sma(df["followers"], 30)
        ema7 = engine.ema(df["followers"], 7)
        reg = engine.linear_regression(df["followers"])

        ts = df["followers"].copy()
        ts.index = pd.to_datetime(df["date"])
        projections = engine.project_values(ts, projection_days)

        data = [
            GrowthPoint(
                date=row["date"],
                value=int(row["followers"]) if pd.notna(row["followers"]) else None,
                growth_rate_pct=round(float(growth.iloc[i]), 4) if pd.notna(growth.iloc[i]) else None,
                sma_7=round(float(sma7.iloc[i]), 2) if pd.notna(sma7.iloc[i]) else None,
                sma_30=round(float(sma30.iloc[i]), 2) if pd.notna(sma30.iloc[i]) else None,
                ema_7=round(float(ema7.iloc[i]), 2) if pd.notna(ema7.iloc[i]) else None,
            )
            for i, row in df.iterrows()
        ]

        return GrowthResponse(
            account_id=account_id, metric="followers",
            regression=RegressionInfo(**reg),
            projections=[ProjectionPoint(**p) for p in projections],
            data=data,
        )

    async def get_content_performance(
        self, account_id: str, date_from: datetime | None, date_to: datetime | None, limit: int = 50
    ) -> ContentPerformanceResponse:
        user = await self._resolve_user(account_id)
        videos = await self._repo.get_top_videos(user["id"], date_from, date_to, limit)

        if not videos:
            return ContentPerformanceResponse(
                account_id=account_id,
                engagement_stats=StatsInfo(**{k: None for k in ["count","mean","median","std","min","max","skewness","kurtosis"]}),
                quartile_distribution=QuartileInfo(q1=0, q2=0, q3=0, q4=0),
                items=[],
            )

        records = []
        for v in videos:
            likes = v["like_count"] or 0
            comments = v["comment_count"] or 0
            shares = v["share_count"] or 0
            views = v["view_count"] or 0
            records.append({
                "id": v["tt_video_id"], "likes": likes, "comments": comments,
                "shares": shares, "views": views,
                "engagement": likes + comments + shares,
            })

        df = pd.DataFrame(records)
        numeric_cols = ["likes", "comments", "shares", "views", "engagement"]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        eng = df["engagement"]

        stats = engine.descriptive_stats(eng)
        quartiles = engine.quartile_distribution(eng)
        z_scores = engine.compute_z_scores(eng)
        percentiles = engine.compute_percentile_ranks(eng)
        scores = engine.composite_score(df, ["likes", "comments", "shares", "views"], [0.3, 0.25, 0.25, 0.2])

        items = [
            ContentItem(
                content_id=row["id"],
                engagement=int(row["engagement"]),
                percentile=round(float(percentiles.iloc[i]), 2),
                z_score=round(float(z_scores.iloc[i]), 4),
                composite_score=float(scores.iloc[i]),
                is_anomaly=abs(float(z_scores.iloc[i])) > 2.0,
            )
            for i, row in df.iterrows()
        ]
        items.sort(key=lambda x: x.composite_score, reverse=True)

        return ContentPerformanceResponse(
            account_id=account_id,
            engagement_stats=StatsInfo(**stats),
            quartile_distribution=QuartileInfo(**quartiles),
            items=items,
        )

    async def get_posting_patterns(
        self, account_id: str, date_from: datetime | None, date_to: datetime | None
    ) -> PostingPatternsResponse:
        user = await self._resolve_user(account_id)
        videos = await self._repo.get_top_videos(user["id"], date_from, date_to, limit=500)

        if not videos:
            return PostingPatternsResponse(
                account_id=account_id, total_content=0, avg_posts_per_week=None,
                by_day_of_week=[], by_hour=[], best_time=None, heatmap=[],
            )

        records = [
            {"date": v["create_time"], "engagement": (v["like_count"] or 0) + (v["comment_count"] or 0) + (v["share_count"] or 0)}
            for v in videos if v["create_time"]
        ]
        df = pd.DataFrame(records)
        if df.empty:
            return PostingPatternsResponse(
                account_id=account_id, total_content=len(videos), avg_posts_per_week=None,
                by_day_of_week=[], by_hour=[], best_time=None, heatmap=[],
            )

        dates = pd.to_datetime(df["date"], utc=True)
        span_weeks = max((dates.max() - dates.min()).days / 7.0, 1.0)

        return PostingPatternsResponse(
            account_id=account_id,
            total_content=len(videos),
            avg_posts_per_week=round(len(df) / span_weeks, 2),
            by_day_of_week=[DayEngagement(**d) for d in engine.engagement_by_day_of_week(df, "date", "engagement")],
            by_hour=[HourEngagement(**h) for h in engine.engagement_by_hour(df, "date", "engagement")],
            best_time=BestTime(**b) if (b := engine.best_posting_time(df, "date", "engagement")) else None,
            heatmap=engine.engagement_heatmap(df, "date", "engagement"),
        )

    async def get_trends(
        self, account_id: str, date_from: datetime | None, date_to: datetime | None,
        split_date: datetime | None = None,
    ) -> TrendsResponse:
        user = await self._resolve_user(account_id)
        trends_data = await self._repo.get_video_snapshot_trends(user["id"], date_from, date_to)

        if not trends_data:
            return TrendsResponse(
                account_id=account_id,
                regression=RegressionInfo(slope=None, intercept=None, r_squared=None, direction="insufficient_data"),
                anomalies=[], period_comparison=None, correlations=[],
            )

        df = pd.DataFrame(trends_data)
        df["date"] = pd.to_datetime(df["date"], utc=True)
        df = df.sort_values("date").reset_index(drop=True)

        numeric_cols = ["total_likes", "total_comments", "total_shares", "total_views"]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        df["engagement"] = (df["total_likes"].fillna(0) + df["total_comments"].fillna(0) + df["total_shares"].fillna(0))

        reg = engine.linear_regression(df["engagement"])

        z = engine.compute_z_scores(df["engagement"])
        anomalies = [
            AnomalyItem(
                content_id=f"snapshot_{i}", date=df.loc[i, "date"],
                value=float(df.loc[i, "engagement"]),
                z_score=round(float(z.iloc[i]), 4),
            )
            for i in df.index[z.abs() > 2.0]
        ]

        period_comp = None
        if split_date:
            comp = engine.period_comparison(df["engagement"], df["date"], split_date)
            period_comp = PeriodComparison(
                before=PeriodStats(**comp["before"]),
                after=PeriodStats(**comp["after"]),
                change_pct=comp["change_pct"],
            )

        correlations = []
        if "total_views" in df.columns:
            overall = float(df["total_views"].corr(df["engagement"])) if len(df) > 1 else None
            rolling = engine.rolling_correlation(df["total_views"], df["engagement"], window=7)
            correlations.append(CorrelationPair(
                metric_a="views", metric_b="engagement",
                overall_correlation=round(overall, 4) if overall is not None and pd.notna(overall) else None,
                rolling=[CorrelationPoint(**r) for r in rolling],
            ))

        return TrendsResponse(
            account_id=account_id,
            regression=RegressionInfo(**reg),
            anomalies=anomalies,
            period_comparison=period_comp,
            correlations=correlations,
        )
