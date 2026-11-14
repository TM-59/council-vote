"""Persistence ports used by the application layer."""

from dataclasses import dataclass
from typing import Protocol

from council_vote.domain import CouncilSession


@dataclass(frozen=True, slots=True)
class VersionedSession:
    version: int
    session: CouncilSession


class SessionRepository(Protocol):
    def add(self, session: CouncilSession) -> None: ...

    def get(self, session_id: str) -> VersionedSession | None: ...

    def save(self, snapshot: VersionedSession) -> bool: ...
