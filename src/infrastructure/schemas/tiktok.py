from datetime import datetime
from pydantic import BaseModel


class TTOverview(BaseModel):
    account_id: str
    display_name: str | None
    followers: int | None
    following: int | None
    total_likes: int | None
    video_count: int | None
    avg_views: float | None
    avg_engagement_rate: float | None


class TTFollowersPoint(BaseModel):
    date: datetime
    follower_count: int | None
    following_count: int | None
    likes_count: int | None
    video_count: int | None


class TTFollowersResponse(BaseModel):
    account_id: str
    data: list[TTFollowersPoint]


class TTVideoItem(BaseModel):
    tt_video_id: str
    title: str | None
    duration: int | None
    share_url: str | None
    create_time: datetime | None
    like_count: int | None
    comment_count: int | None
    share_count: int | None
    view_count: int | None
    engagement_rate: float | None


class TTVideosResponse(BaseModel):
    account_id: str
    total_videos: int
    data: list[TTVideoItem]


class TTEngagementPoint(BaseModel):
    date: datetime
    total_likes: int | None
    total_comments: int | None
    total_shares: int | None
    total_views: int | None
    engagement_rate: float | None


class TTEngagementResponse(BaseModel):
    account_id: str
    data: list[TTEngagementPoint]
