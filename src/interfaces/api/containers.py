from dependency_injector import containers, providers
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.models.base import async_session_factory
from src.infrastructure.repositories.instagram_repository import InstagramRepository
from src.infrastructure.repositories.tiktok_repository import TikTokRepository
from src.infrastructure.repositories.youtube_repository import YouTubeRepository
from src.application.services.instagram_service import InstagramAnalyticsService
from src.application.services.tiktok_service import TikTokAnalyticsService
from src.application.services.youtube_service import YouTubeAnalyticsService


class Container(containers.DeclarativeContainer):
    wiring_config = containers.WiringConfiguration(
        modules=[
            "src.interfaces.api.routers.instagram",
            "src.interfaces.api.routers.tiktok",
            "src.interfaces.api.routers.youtube",
        ]
    )

    session_factory = providers.Singleton(lambda: async_session_factory)

    instagram_repository = providers.Factory(
        InstagramRepository,
        session=providers.Dependency(instance_of=AsyncSession),
    )

    tiktok_repository = providers.Factory(
        TikTokRepository,
        session=providers.Dependency(instance_of=AsyncSession),
    )

    youtube_repository = providers.Factory(
        YouTubeRepository,
        session=providers.Dependency(instance_of=AsyncSession),
    )

    instagram_service = providers.Factory(
        InstagramAnalyticsService,
        repository=instagram_repository,
    )

    tiktok_service = providers.Factory(
        TikTokAnalyticsService,
        repository=tiktok_repository,
    )

    youtube_service = providers.Factory(
        YouTubeAnalyticsService,
        repository=youtube_repository,
    )
