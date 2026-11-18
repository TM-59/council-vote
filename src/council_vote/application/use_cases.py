"""Framework-independent session use cases."""

from typing import TYPE_CHECKING
from uuid import uuid4

from council_vote.domain import Agenda, CouncilSession, Event

if TYPE_CHECKING:
    from collections.abc import Callable

    from .ports import SessionRepository


class SessionNotFoundError(Exception):
    """No session exists with the requested identity."""


class SessionConflictError(Exception):
    """The session changed after it was read."""


def _new_session_id() -> str:
    return uuid4().hex


class StartSession:
    """Create a new session and store it."""

    def __init__(
        self, repository: SessionRepository, id_factory: Callable[[], str] = _new_session_id
    ) -> None:
        """Use `repository` for storage and `id_factory` for new identities."""
        self.repository = repository
        self.id_factory = id_factory

    def execute(self) -> CouncilSession:
        """Start a session at the first council and return it."""
        session = CouncilSession(self.id_factory())
        self.repository.add(session)
        return session


class ResolveAgenda:
    """Put an agenda to the sitting council of a stored session."""

    def __init__(self, repository: SessionRepository) -> None:
        """Use `repository` to read and save sessions."""
        self.repository = repository

    def execute(self, session_id: str, agenda: Agenda) -> tuple[Event, ...]:
        """Resolve `agenda` in the session and save it; return the events that happened."""
        snapshot = self.repository.get(session_id)
        if snapshot is None:
            raise SessionNotFoundError(session_id)
        events = snapshot.session.resolve(agenda)
        if not self.repository.save(snapshot):
            raise SessionConflictError(session_id)
        return events


class ReadSession:
    """Read a stored session."""

    def __init__(self, repository: SessionRepository) -> None:
        """Use `repository` to read sessions."""
        self.repository = repository

    def execute(self, session_id: str) -> CouncilSession:
        """Return the stored session with identity `session_id`."""
        snapshot = self.repository.get(session_id)
        if snapshot is None:
            raise SessionNotFoundError(session_id)
        return snapshot.session
