from datetime import datetime
from pydantic import BaseModel


class GrowthPoint(BaseModel):
    date: datetime
    value: int | None
    growth_rate_pct: float | None = None
    sma_7: float | None = None
    sma_30: float | None = None
    ema_7: float | None = None


class RegressionInfo(BaseModel):
    slope: float | None
    relative_slope: float | None = 0.0
    intercept: float | None
    r_squared: float | None
    direction: str


class ProjectionPoint(BaseModel):
    day_offset: int
    projected_value: float
    date: str | None = None


class GrowthResponse(BaseModel):
    account_id: str
    metric: str
    regression: RegressionInfo
    projections: list[ProjectionPoint]
    data: list[GrowthPoint]


class StatsInfo(BaseModel):
    count: int | None
    mean: float | None
    median: float | None
    std: float | None
    min: float | None
    max: float | None
    skewness: float | None
    kurtosis: float | None


class QuartileInfo(BaseModel):
    q1: int
    q2: int
    q3: int
    q4: int


class ContentItem(BaseModel):
    content_id: str
    title: str | None = None
    caption: str | None = None
    thumbnail_url: str | None = None
    permalink: str | None = None
    engagement: int
    percentile: float
    z_score: float
    composite_score: float
    is_anomaly: bool = False


class ContentPerformanceResponse(BaseModel):
    account_id: str
    engagement_stats: StatsInfo
    quartile_distribution: QuartileInfo
    items: list[ContentItem]


class DayEngagement(BaseModel):
    day: str
    day_index: int
    avg_engagement: float


class HourEngagement(BaseModel):
    hour: int
    avg_engagement: float


class BestTime(BaseModel):
    day: str
    day_index: int
    hour: int
    avg_engagement: float


class PostingPatternsResponse(BaseModel):
    account_id: str
    total_content: int
    avg_posts_per_week: float | None
    by_day_of_week: list[DayEngagement]
    by_hour: list[HourEngagement]
    best_time: BestTime | None
    heatmap: list[list[float]]



class AnomalyItem(BaseModel):
    content_id: str
    date: datetime | None
    value: float
    z_score: float


class CorrelationPoint(BaseModel):
    index: int
    correlation: float


class PeriodStats(BaseModel):
    mean: float | None
    median: float | None
    total: float | None
    count: int


class PeriodComparison(BaseModel):
    before: PeriodStats
    after: PeriodStats
    change_pct: float | None


class CorrelationPair(BaseModel):
    metric_a: str
    metric_b: str
    overall_correlation: float | None
    rolling: list[CorrelationPoint]


class TrendsResponse(BaseModel):
    account_id: str
    regression: RegressionInfo
    anomalies: list[AnomalyItem]
    period_comparison: PeriodComparison | None
    correlations: list[CorrelationPair]
    projections: list[ProjectionPoint] = []
    data: list[GrowthPoint] = []
