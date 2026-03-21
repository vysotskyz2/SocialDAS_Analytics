from datetime import datetime
from pydantic import BaseModel


class YTOverview(BaseModel):
    account_id: str
    title: str | None
    subscribers: int | None
    total_views: int | None
    video_count: int | None
    avg_views_per_video: float | None
    avg_engagement_rate: float | None


class YTSubscribersPoint(BaseModel):
    date: datetime
    subscriber_count: int | None
    video_count: int | None
    view_count: int | None


class YTSubscribersResponse(BaseModel):
    account_id: str
    data: list[YTSubscribersPoint]


class YTVideoItem(BaseModel):
    yt_video_id: str
    title: str | None
    published_at: datetime | None
    duration: str | None
    view_count: int | None
    like_count: int | None
    comment_count: int | None
    engagement_rate: float | None


class YTVideosResponse(BaseModel):
    account_id: str
    total_videos: int
    data: list[YTVideoItem]


class YTEngagementPoint(BaseModel):
    date: datetime
    total_views: int | None
    total_likes: int | None
    total_comments: int | None
    engagement_rate: float | None


class YTEngagementResponse(BaseModel):
    account_id: str
    data: list[YTEngagementPoint]
