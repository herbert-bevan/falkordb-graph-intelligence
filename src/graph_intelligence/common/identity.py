"""Trusted identity resolution for user-scoped operations."""

from dataclasses import dataclass
from graph_intelligence.common.config import get_settings


@dataclass(frozen=True)
class TrustedIdentity:
    user_id: str

    @classmethod
    def current(cls) -> "TrustedIdentity":
        """Resolve current trusted user identity from environment/config."""
        settings = get_settings()
        return cls(user_id=settings.DEMO_USER_ID)
