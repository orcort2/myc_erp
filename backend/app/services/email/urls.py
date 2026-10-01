"""Public application URL used to build links inside emails."""

from app.core.config import Settings

DEVELOPMENT_BASE_URL = "http://localhost:5173"


def is_production(settings: Settings) -> bool:
    return settings.environment.strip().lower() in {"production", "prod"}


def resolve_public_base_url(settings: Settings) -> str | None:
    """PUBLIC_APP_BASE_URL, else legacy PORTAL_PUBLIC_BASE_URL; dev-only fallback.

    Returns None in production when neither is configured (callers must not send).
    """
    configured = settings.effective_public_base_url
    if configured:
        return configured
    return None if is_production(settings) else DEVELOPMENT_BASE_URL
