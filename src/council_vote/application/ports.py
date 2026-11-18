"""Persistence ports used by the application layer."""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from council_vote.domain import CouncilSession


@dataclass(frozen=True, slots=True)
class VersionedSession:
    """A session as read from storage, with the version it was read at."""

    version: int
    session: CouncilSession


class SessionRepository(Protocol):
    """Port for storing sessions; `save` succeeds only for the version that was read."""

    def add(self, session: CouncilSession) -> None:
        """Store a new session at version 0."""

    def get(self, session_id: str) -> VersionedSession | None:
        """Return the session and its version, or None when it does not exist."""

    def save(self, snapshot: VersionedSession) -> bool:
        """Write the session if nobody saved it since it was read; return whether it was written."""
