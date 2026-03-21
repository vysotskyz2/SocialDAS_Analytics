from contextvars import ContextVar
from dependency_injector import containers, providers
from sqlalchemy.ext.asyncio import AsyncSession
from src.infrastructure.repositories.instagram_repository import InstagramRepository
from src.infrastructure.repositories.tiktok_repository import TikTokRepository
from src.infrastructure.repositories.youtube_repository import YouTubeRepository
from src.application.services.instagram_service import InstagramAnalyticsService
from src.application.services.tiktok_service import TikTokAnalyticsService
from src.application.services.youtube_service import YouTubeAnalyticsService
from src.application.services.instagram_advanced import InstagramAdvancedService
from src.application.services.tiktok_advanced import TikTokAdvancedService
from src.application.services.youtube_advanced import YouTubeAdvancedService


db_session_context: ContextVar[AsyncSession] = ContextVar("db_session_context")


def get_db_session() -> AsyncSession:
    return db_session_context.get()


class Container(containers.DeclarativeContainer):
    wiring_config = containers.WiringConfiguration(
        modules=[
            "src.interfaces.api.routers.instagram",
            "src.interfaces.api.routers.tiktok",
            "src.interfaces.api.routers.youtube",
            "src.interfaces.api.routers.instagram_advanced",
            "src.interfaces.api.routers.tiktok_advanced",
            "src.interfaces.api.routers.youtube_advanced",
            "src.interfaces.api.app",
        ]
    )

    db_session = providers.Callable(get_db_session)


    instagram_repository = providers.Factory(
        InstagramRepository,
        session=db_session,
    )

    tiktok_repository = providers.Factory(
        TikTokRepository,
        session=db_session,
    )

    youtube_repository = providers.Factory(
        YouTubeRepository,
        session=db_session,
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

    instagram_advanced_service = providers.Factory(
        InstagramAdvancedService,
        repository=instagram_repository,
    )

    tiktok_advanced_service = providers.Factory(
        TikTokAdvancedService,
        repository=tiktok_repository,
    )

    youtube_advanced_service = providers.Factory(
        YouTubeAdvancedService,
        repository=youtube_repository,
    )
