"""Use cases against an in-memory repository port."""

import copy
from dataclasses import dataclass, field
from typing import cast

import pytest

from council_vote.application.ports import VersionedSession
from council_vote.application.use_cases import (
    ReadSession,
    ResolveAgenda,
    SessionConflictError,
    SessionNotFoundError,
    StartSession,
)
from council_vote.domain import (
    ATTEMPTS_PER_COUNCIL,
    Agenda,
    CouncilSession,
    NotAnAgendaError,
    SessionFinishedError,
)

WINNING = (
    Agenda(lamps=True, gate=True, bell=False),
    Agenda(lamps=False, gate=False, bell=True),
    Agenda(lamps=False, gate=True, bell=True),
)


@dataclass
class MemorySessionRepository:
    """In-memory SessionRepository with optimistic versioning and an injectable conflict."""

    sessions: dict[str, VersionedSession] = field(default_factory=dict)
    conflict_on_save: bool = False

    def add(self, session: CouncilSession) -> None:
        """Store a copy of the session at version 0."""
        self.sessions[session.session_id] = VersionedSession(0, copy.deepcopy(session))

    def get(self, session_id: str) -> VersionedSession | None:
        """Return a copy of the stored session and its version."""
        snapshot = self.sessions.get(session_id)
        if snapshot is None:
            return None
        return VersionedSession(snapshot.version, copy.deepcopy(snapshot.session))

    def save(self, snapshot: VersionedSession) -> bool:
        """Save when the version matches and no conflict is injected."""
        current = self.sessions.get(snapshot.session.session_id)
        if self.conflict_on_save or current is None or current.version != snapshot.version:
            return False
        self.sessions[snapshot.session.session_id] = VersionedSession(
            current.version + 1, copy.deepcopy(snapshot.session)
        )
        return True


def test_req_usecase_start_resolve_and_read_use_the_repository_port() -> None:
    """REQ-USECASE: start, resolve and read go through the port."""
    repository = MemorySessionRepository()
    session = StartSession(repository, id_factory=lambda: "session-1").execute()

    events = ResolveAgenda(repository).execute(session.session_id, WINNING[0])
    restored = ReadSession(repository).execute(session.session_id)

    assert session.session_id == "session-1"
    assert len(events) == 1
    assert restored.council == 1
    assert restored.attempts_left == ATTEMPTS_PER_COUNCIL
    assert restored.history[0].agenda == WINNING[0]


def test_req_usecase_missing_and_conflicting_sessions_are_explicit() -> None:
    """REQ-USECASE: a missing session and a lost update raise their own errors."""
    repository = MemorySessionRepository()
    with pytest.raises(SessionNotFoundError):
        ReadSession(repository).execute("missing")

    session = StartSession(repository, id_factory=lambda: "session-2").execute()
    repository.conflict_on_save = True
    with pytest.raises(SessionConflictError):
        ResolveAgenda(repository).execute(session.session_id, WINNING[0])


@pytest.mark.parametrize("finish", [True, False])
def test_req_usecase_finished_or_invalid_resolution_does_not_save(*, finish: bool) -> None:
    """REQ-USECASE: a refused resolution leaves the stored session unchanged."""
    repository = MemorySessionRepository()
    session = StartSession(repository, id_factory=lambda: "session-3").execute()
    resolve = ResolveAgenda(repository)
    if finish:
        for agenda in WINNING:
            resolve.execute(session.session_id, agenda)
        before = repository.get(session.session_id)
        assert before is not None
        with pytest.raises(SessionFinishedError):
            resolve.execute(session.session_id, WINNING[0])
    else:
        before = repository.get(session.session_id)
        assert before is not None
        with pytest.raises(NotAnAgendaError):
            resolve.execute(session.session_id, cast("Agenda", None))
    after = repository.get(session.session_id)
    assert before == after
