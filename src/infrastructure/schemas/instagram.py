from datetime import datetime
from pydantic import BaseModel


class IGOverview(BaseModel):
    account_id: str
    username: str | None
    followers: int | None
    following: int | None
    media_count: int | None
    total_likes: int
    total_comments: int
    avg_engagement_rate: float | None


class IGFollowersPoint(BaseModel):
    date: datetime
    followers: int | None
    follows: int | None
    media_count: int | None


class IGFollowersResponse(BaseModel):
    account_id: str
    data: list[IGFollowersPoint]


class IGPostItem(BaseModel):
    ig_id: str
    media_type: str | None
    caption: str | None
    permalink: str | None
    timestamp: datetime | None
    like_count: int | None
    comments_count: int | None
    engagement: int
    reach: int | None
    saved: int | None
    views: int | None
    shares: int | None


class IGPostsResponse(BaseModel):
    account_id: str
    total_posts: int
    data: list[IGPostItem]


class IGEngagementPoint(BaseModel):
    date: datetime
    period: str
    reach: int | None
    profile_views: int | None
    views: int | None
    likes: int | None
    comments: int | None
    shares: int | None
    saves: int | None
    website_clicks: int | None


class IGEngagementResponse(BaseModel):
    account_id: str
    data: list[IGEngagementPoint]
