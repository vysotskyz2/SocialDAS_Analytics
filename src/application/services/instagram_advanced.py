from datetime import datetime
import pandas as pd
from fastapi import HTTPException, status
from src.application.services import analytics_engine as engine
from src.infrastructure.repositories.instagram_repository import InstagramRepository
from src.infrastructure.schemas.advanced import (
    GrowthResponse, GrowthPoint, RegressionInfo, ProjectionPoint,
    ContentPerformanceResponse, ContentItem, StatsInfo, QuartileInfo,
    PostingPatternsResponse, DayEngagement, HourEngagement, BestTime,
    TrendsResponse, AnomalyItem, CorrelationPair, CorrelationPoint, PeriodComparison, PeriodStats,
)


class InstagramAdvancedService:
    def __init__(self, repository: InstagramRepository) -> None:
        self._repo = repository

    async def _resolve_user(self, account_id: str):
        user = await self._repo.get_user_by_ig_id(account_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Instagram account not found")
        return user

    async def get_growth(
            self, account_id: str, date_from: datetime | None, date_to: datetime | None, projection_days: int = 14
    ) -> GrowthResponse:
        user = await self._resolve_user(account_id)
        snapshots = await self._repo.get_follower_snapshots(user["id"], date_from, date_to)

        records = [{"date": s["date"], "followers": s["followers_count"]} for s in snapshots]
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

        data = []
        for i, row in df.iterrows():
            data.append(GrowthPoint(
                date=row["date"],
                value=int(row["followers"]) if pd.notna(row["followers"]) else None,
                growth_rate_pct=round(float(growth.iloc[i]), 4) if pd.notna(growth.iloc[i]) else None,
                sma_7=round(float(sma7.iloc[i]), 2) if pd.notna(sma7.iloc[i]) else None,
                sma_30=round(float(sma30.iloc[i]), 2) if pd.notna(sma30.iloc[i]) else None,
                ema_7=round(float(ema7.iloc[i]), 2) if pd.notna(ema7.iloc[i]) else None,
            ))

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
        posts = await self._repo.get_top_posts(user["id"], date_from, date_to, limit)

        if not posts:
            return ContentPerformanceResponse(
                account_id=account_id,
                engagement_stats=StatsInfo(
                    **{k: None for k in ["count", "mean", "median", "std", "min", "max", "skewness", "kurtosis"]}),
                quartile_distribution=QuartileInfo(q1=0, q2=0, q3=0, q4=0),
                items=[],
            )

        records = []
        for p in posts:
            likes = p["like_count"] or 0
            comments = p["comments_count"] or 0
            records.append({
                "id": p["ig_id"], 
                "likes": likes, 
                "comments": comments, 
                "engagement": likes + comments,
                "caption": p.get("caption"),
                "permalink": p.get("permalink"),
                "thumbnail_url": p.get("thumbnail_url") or p.get("media_url")
            })

        df = pd.DataFrame(records)
        for col in ["likes", "comments", "engagement"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        eng = df["engagement"]

        stats = engine.descriptive_stats(eng)
        quartiles = engine.quartile_distribution(eng)
        z_scores = engine.compute_z_scores(eng)
        percentiles = engine.compute_percentile_ranks(eng)
        scores = engine.composite_score(df, ["likes", "comments"])

        items = []
        for i, row in df.iterrows():
            items.append(ContentItem(
                content_id=row["id"],
                caption=row.get("caption"),
                permalink=row.get("permalink"),
                thumbnail_url=row.get("thumbnail_url"),
                engagement=int(row["engagement"]),
                percentile=round(float(percentiles.iloc[i]), 4),
                z_score=round(float(z_scores.iloc[i]), 4),
                composite_score=float(scores.iloc[i]),
                is_anomaly=abs(float(z_scores.iloc[i])) > 2.0,
            ))

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
        posts = await self._repo.get_top_posts(user["id"], date_from, date_to, limit=500)

        if not posts:
            return PostingPatternsResponse(
                account_id=account_id, total_content=0, avg_posts_per_week=None,
                by_day_of_week=[], by_hour=[], best_time=None, heatmap=[],
            )

        records = [
            {"date": p["timestamp"], "engagement": (p["like_count"] or 0) + (p["comments_count"] or 0)}
            for p in posts if p["timestamp"]
        ]
        df = pd.DataFrame(records)
        if df.empty:
            return PostingPatternsResponse(
                account_id=account_id, total_content=len(posts), avg_posts_per_week=None,
                by_day_of_week=[], by_hour=[], best_time=None, heatmap=[],
            )

        dates = pd.to_datetime(df["date"], utc=True)
        span_weeks = max((dates.max() - dates.min()).days / 7.0, 1.0)
        avg_per_week = round(len(df) / span_weeks, 2)

        by_dow = engine.engagement_by_day_of_week(df, "date", "engagement")
        by_hour = engine.engagement_by_hour(df, "date", "engagement")
        heatmap = engine.engagement_heatmap(df, "date", "engagement")
        best = engine.best_posting_time(df, "date", "engagement")

        return PostingPatternsResponse(
            account_id=account_id,
            total_content=len(posts),
            avg_posts_per_week=avg_per_week,
            by_day_of_week=[DayEngagement(**d) for d in by_dow],
            by_hour=[HourEngagement(**h) for h in by_hour],
            best_time=BestTime(**best) if best else None,
            heatmap=heatmap,
        )

    async def get_trends(
            self, account_id: str, date_from: datetime | None, date_to: datetime | None,
            split_date: datetime | None = None,
    ) -> TrendsResponse:
        user = await self._resolve_user(account_id)
        insights = await self._repo.get_profile_insights(user["id"], date_from, date_to)

        if not insights:
            return TrendsResponse(
                account_id=account_id,
                regression=RegressionInfo(slope=None, intercept=None, r_squared=None, direction="insufficient_data"),
                anomalies=[], period_comparison=None, correlations=[],
            )

        records = []
        for i in insights:
            records.append({
                "date": i["date"],
                "reach": i["reach"] or 0,
                "views": i["views"] or 0,
                "likes": i["likes"] or 0,
                "comments": i["comments"] or 0,
                "shares": i["shares"] or 0,
            })

        df = pd.DataFrame(records)
        df["date"] = pd.to_datetime(df["date"], utc=True)
        df = df.sort_values("date").reset_index(drop=True)
        
        numeric_cols = ["reach", "views", "likes", "comments", "shares"]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        df["engagement"] = df["likes"] + df["comments"] + df["shares"]

        reg = engine.linear_regression(df["engagement"])

        z = engine.compute_z_scores(df["engagement"])
        anomaly_mask = z.abs() > 2.0
        anomalies = [
            AnomalyItem(
                content_id=f"insight_{i}",
                date=df.loc[i, "date"],
                value=float(df.loc[i, "engagement"]),
                z_score=round(float(z.iloc[i]), 4),
            )
            for i in df.index[anomaly_mask]
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
        pairs = [("reach", "engagement"), ("views", "likes")]
        for a, b in pairs:
            if a in df.columns and b in df.columns:
                overall = float(df[a].corr(df[b])) if len(df) > 1 else None
                rolling = engine.rolling_correlation(df[a], df[b], window=7)
                correlations.append(CorrelationPair(
                    metric_a=a, metric_b=b,
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
