"""Framework-independent session use cases."""

from collections.abc import Callable
from uuid import uuid4

from council_vote.domain import Agenda, CouncilSession, Event

from .ports import SessionRepository


class SessionNotFound(Exception):
    """No session exists with the requested identity."""


class SessionConflict(Exception):
    """The session changed after it was read."""


def _new_session_id() -> str:
    return uuid4().hex


class StartSession:
    def __init__(
        self, repository: SessionRepository, id_factory: Callable[[], str] = _new_session_id
    ) -> None:
        self.repository = repository
        self.id_factory = id_factory

    def execute(self) -> CouncilSession:
        session = CouncilSession(self.id_factory())
        self.repository.add(session)
        return session


class ResolveAgenda:
    def __init__(self, repository: SessionRepository) -> None:
        self.repository = repository

    def execute(self, session_id: str, agenda: Agenda) -> tuple[Event, ...]:
        snapshot = self.repository.get(session_id)
        if snapshot is None:
            raise SessionNotFound(session_id)
        events = snapshot.session.resolve(agenda)
        if not self.repository.save(snapshot):
            raise SessionConflict(session_id)
        return events


class ReadSession:
    def __init__(self, repository: SessionRepository) -> None:
        self.repository = repository

    def execute(self, session_id: str) -> CouncilSession:
        snapshot = self.repository.get(session_id)
        if snapshot is None:
            raise SessionNotFound(session_id)
        return snapshot.session
