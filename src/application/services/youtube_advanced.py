import asyncio
from datetime import datetime
import pandas as pd
from fastapi import HTTPException, status
from src.application.services import analytics_engine as engine
from src.infrastructure.repositories.youtube_repository import YouTubeRepository
from src.infrastructure.schemas.advanced import (
    GrowthResponse, GrowthPoint, RegressionInfo, ProjectionPoint,
    ContentPerformanceResponse, ContentItem, StatsInfo, QuartileInfo,
    PostingPatternsResponse, DayEngagement, HourEngagement, BestTime,
    TrendsResponse, AnomalyItem, CorrelationPair, CorrelationPoint, PeriodComparison, PeriodStats,
)


class YouTubeAdvancedService:
    def __init__(self, repository: YouTubeRepository) -> None:
        self._repo = repository

    async def _resolve_channel(self, account_id: str):
        channel = await self._repo.get_channel_by_yt_id(account_id)
        if not channel:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="YouTube channel not found")
        return channel

    async def get_growth(
        self, account_id: str, date_from: datetime | None, date_to: datetime | None, projection_days: int = 14
    ) -> GrowthResponse:
        channel = await self._resolve_channel(account_id)
        snapshots = await self._repo.get_subscriber_snapshots(channel["id"], date_from, date_to)

        records = [{"date": s["date"], "subscribers": s["subscriber_count"]} for s in snapshots]
        df = await asyncio.to_thread(engine.build_time_series, records, "date", "subscribers")

        if df.empty:
            return GrowthResponse(
                account_id=account_id, metric="subscribers",
                regression=RegressionInfo(slope=None, intercept=None, r_squared=None, direction="insufficient_data"),
                projections=[], data=[],
            )

        # Math tasks offloaded to threads
        growth_task = asyncio.to_thread(engine.compute_growth_rates, df["subscribers"])
        sma7_task = asyncio.to_thread(engine.sma, df["subscribers"], 7)
        sma30_task = asyncio.to_thread(engine.sma, df["subscribers"], 30)
        ema7_task = asyncio.to_thread(engine.ema, df["subscribers"], 7)
        reg_task = asyncio.to_thread(engine.linear_regression, df["subscribers"])

        growth, sma7, sma30, ema7, reg = await asyncio.gather(
            growth_task, sma7_task, sma30_task, ema7_task, reg_task
        )

        ts = df["subscribers"].copy()
        ts.index = pd.to_datetime(df["date"])
        projections = await asyncio.to_thread(engine.project_values, ts, projection_days)

        data = [
            GrowthPoint(
                date=row["date"],
                value=int(row["subscribers"]) if pd.notna(row["subscribers"]) else None,
                growth_rate_pct=round(float(growth.iloc[i]), 4) if pd.notna(growth.iloc[i]) else None,
                sma_7=round(float(sma7.iloc[i]), 2) if pd.notna(sma7.iloc[i]) else None,
                sma_30=round(float(sma30.iloc[i]), 2) if pd.notna(sma30.iloc[i]) else None,
                ema_7=round(float(ema7.iloc[i]), 2) if pd.notna(ema7.iloc[i]) else None,
            )
            for i, row in df.iterrows()
        ]

        return GrowthResponse(
            account_id=account_id, metric="subscribers",
            regression=RegressionInfo(**reg),
            projections=[ProjectionPoint(**p) for p in projections],
            data=data,
        )

    async def get_content_performance(
        self, account_id: str, date_from: datetime | None, date_to: datetime | None, limit: int = 50
    ) -> ContentPerformanceResponse:
        channel = await self._resolve_channel(account_id)
        rows = await self._repo.get_top_videos(channel["id"], date_from, date_to, limit)

        if not rows:
            return ContentPerformanceResponse(
                account_id=account_id,
                engagement_stats=StatsInfo(**{k: None for k in ["count","mean","median","std","min","max","skewness","kurtosis"]}),
                quartile_distribution=QuartileInfo(q1=0, q2=0, q3=0, q4=0),
                items=[],
            )

        records = []
        for row in rows:
            likes = int(row["like_count"] or 0)
            comments = int(row["comment_count"] or 0)
            views = int(row["view_count"] or 0)
            video_id = row["yt_video_id"]
            records.append({
                "id": video_id, 
                "likes": likes, 
                "comments": comments,
                "views": views, 
                "engagement": likes + comments,
                "title": row["title"],
                "caption": row["description"],
                "permalink": f"https://www.youtube.com/watch?v={video_id}",
                "thumbnail_url": row["thumbnail_url"]
            })

        def process_content():
            df = pd.DataFrame(records)
            for col in ["likes", "comments", "views", "engagement"]:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors="coerce")
            eng = df["engagement"]

            return (
                df,
                engine.descriptive_stats(eng),
                engine.quartile_distribution(eng),
                engine.compute_z_scores(eng),
                engine.compute_percentile_ranks(eng),
                engine.composite_score(df, ["likes", "comments", "views"], [0.35, 0.3, 0.35])
            )

        df, stats, quartiles, z_scores, percentiles, scores = await asyncio.to_thread(process_content)

        items = [
            ContentItem(
                content_id=row["id"],
                title=row.get("title"),
                caption=row.get("caption"),
                thumbnail_url=row.get("thumbnail_url"),
                permalink=row.get("permalink"),
                engagement=int(row["engagement"]),
                percentile=round(float(percentiles.iloc[i]), 4),
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
        channel = await self._resolve_channel(account_id)
        rows = await self._repo.get_top_videos(channel["id"], date_from, date_to, limit=500)

        if not rows:
            return PostingPatternsResponse(
                account_id=account_id, total_content=0, avg_posts_per_week=None,
                by_day_of_week=[], by_hour=[], best_time=None, heatmap=[],
            )

        records = [
            {"date": row["published_at"], "engagement": int(row["like_count"] or 0) + int(row["comment_count"] or 0)}
            for row in rows if row["published_at"]
        ]
        
        def process_patterns():
            df = pd.DataFrame(records)
            if df.empty: return df, 0, [], [], None, []
            
            dates = pd.to_datetime(df["date"], utc=True)
            span_weeks = max((dates.max() - dates.min()).days / 7.0, 1.0)
            avg_per_week = round(len(df) / span_weeks, 2)
            
            return (
                df, avg_per_week,
                engine.engagement_by_day_of_week(df, "date", "engagement"),
                engine.engagement_by_hour(df, "date", "engagement"),
                engine.best_posting_time(df, "date", "engagement"),
                engine.engagement_heatmap(df, "date", "engagement")
            )

        df, avg_per_week, by_dow, by_hour, best, heatmap = await asyncio.to_thread(process_patterns)

        if df.empty:
            return PostingPatternsResponse(
                account_id=account_id, total_content=len(rows), avg_posts_per_week=None,
                by_day_of_week=[], by_hour=[], best_time=None, heatmap=[],
            )

        return PostingPatternsResponse(
            account_id=account_id,
            total_content=len(rows),
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
        channel = await self._resolve_channel(account_id)
        trends_data = await self._repo.get_video_snapshot_trends(channel["id"], date_from, date_to)

        if not trends_data:
            return TrendsResponse(
                account_id=account_id,
                regression=RegressionInfo(slope=None, intercept=None, r_squared=None, direction="insufficient_data"),
                anomalies=[], period_comparison=None, correlations=[],
            )

        def process_trends():
            df = pd.DataFrame(trends_data)
            df["date"] = pd.to_datetime(df["date"], utc=True)
            df = df.sort_values("date").reset_index(drop=True)

            numeric_cols = ["total_likes", "total_comments", "total_views"]
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors="coerce")

            df["engagement"] = (df["total_likes"].fillna(0) + df["total_comments"].fillna(0))
            
            if len(df) < 2: return df, None, None, None, [], [], None, None

            reg = engine.linear_regression(df["engagement"])
            z = engine.compute_z_scores(df["engagement"])
            
            # Engagement averages and projections
            sma7 = engine.sma(df["engagement"], 7)
            sma30 = engine.sma(df["engagement"], 30)
            
            # Engagement projections
            ts = df["engagement"].copy()
            ts.index = df["date"]
            projections = engine.project_values(ts, 14)
            
            comp = None
            if split_date:
                comp = engine.period_comparison(df["engagement"], df["date"], split_date)
                
            corrs = []
            if "total_views" in df.columns:
                overall = float(df["total_views"].corr(df["engagement"])) if len(df) > 1 else None
                rolling = engine.rolling_correlation(df["total_views"], df["engagement"], window=7)
                corrs.append({"overall": overall, "rolling": rolling})
                
            return df, reg, z, comp, corrs, projections, sma7, sma30

        df, reg, z, comp, corrs_data, projections_data, sma7_data, sma30_data = await asyncio.to_thread(process_trends)

        if len(df) < 2:
            return TrendsResponse(
                account_id=account_id,
                regression=RegressionInfo(slope=0.0, intercept=0.0, r_squared=0.0, direction="insufficient_data"),
                anomalies=[], period_comparison=None, correlations=[],
                projections=[], data=[],
            )

        anomalies = [
            AnomalyItem(
                content_id=f"snapshot_{i}", date=df.loc[i, "date"],
                value=float(df.loc[i, "engagement"]),
                z_score=round(float(z.iloc[i]), 4),
            )
            for i in df.index[z.abs() > 2.0]
        ]

        historical_data = [
            GrowthPoint(
                date=df.loc[i, "date"],
                value=int(df.loc[i, "engagement"]),
                sma_7=round(float(sma7_data.iloc[i]), 2) if pd.notna(sma7_data.iloc[i]) else None,
                sma_30=round(float(sma30_data.iloc[i]), 2) if pd.notna(sma30_data.iloc[i]) else None,
            )
            for i in df.index
        ]

        period_comp = None
        if comp:
            period_comp = PeriodComparison(
                before=PeriodStats(**comp["before"]),
                after=PeriodStats(**comp["after"]),
                change_pct=comp["change_pct"],
            )

        correlations = []
        for c in corrs_data:
            correlations.append(CorrelationPair(
                metric_a="views", metric_b="engagement",
                overall_correlation=round(c["overall"], 4) if c["overall"] is not None and pd.notna(c["overall"]) else None,
                rolling=[CorrelationPoint(**r) for r in c["rolling"]],
            ))

        return TrendsResponse(
            account_id=account_id,
            regression=RegressionInfo(**reg),
            anomalies=anomalies,
            period_comparison=period_comp,
            correlations=correlations,
            projections=[ProjectionPoint(**p) for p in projections_data],
            data=historical_data,
        )
