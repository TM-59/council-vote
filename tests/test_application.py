import copy
from dataclasses import dataclass, field

import pytest

from council_vote.application.ports import VersionedSession
from council_vote.application.use_cases import (
    ReadSession,
    ResolveAgenda,
    SessionConflict,
    SessionNotFound,
    StartSession,
)
from council_vote.domain import Agenda, CouncilSession, SessionFinished

WINNING = (Agenda(True, True, False), Agenda(False, False, True), Agenda(False, True, True))


@dataclass
class MemorySessionRepository:
    sessions: dict[str, VersionedSession] = field(default_factory=dict)
    conflict_on_save: bool = False

    def add(self, session: CouncilSession) -> None:
        self.sessions[session.session_id] = VersionedSession(0, copy.deepcopy(session))

    def get(self, session_id: str) -> VersionedSession | None:
        snapshot = self.sessions.get(session_id)
        if snapshot is None:
            return None
        return VersionedSession(snapshot.version, copy.deepcopy(snapshot.session))

    def save(self, snapshot: VersionedSession) -> bool:
        current = self.sessions.get(snapshot.session.session_id)
        if self.conflict_on_save or current is None or current.version != snapshot.version:
            return False
        self.sessions[snapshot.session.session_id] = VersionedSession(
            current.version + 1, copy.deepcopy(snapshot.session)
        )
        return True


def test_REQ_USECASE_start_resolve_and_read_use_the_repository_port() -> None:
    repository = MemorySessionRepository()
    session = StartSession(repository, id_factory=lambda: "session-1").execute()

    events = ResolveAgenda(repository).execute(session.session_id, WINNING[0])
    restored = ReadSession(repository).execute(session.session_id)

    assert session.session_id == "session-1"
    assert len(events) == 1
    assert restored.council == 1
    assert restored.attempts_left == 2
    assert restored.history[0].agenda == WINNING[0]


def test_REQ_USECASE_missing_and_conflicting_sessions_are_explicit() -> None:
    repository = MemorySessionRepository()
    with pytest.raises(SessionNotFound):
        ReadSession(repository).execute("missing")

    session = StartSession(repository, id_factory=lambda: "session-2").execute()
    repository.conflict_on_save = True
    with pytest.raises(SessionConflict):
        ResolveAgenda(repository).execute(session.session_id, WINNING[0])


@pytest.mark.parametrize("finish", [True, False])
def test_REQ_USECASE_finished_or_invalid_resolution_does_not_save(finish: bool) -> None:
    repository = MemorySessionRepository()
    session = StartSession(repository, id_factory=lambda: "session-3").execute()
    resolve = ResolveAgenda(repository)
    if finish:
        for agenda in WINNING:
            resolve.execute(session.session_id, agenda)
        before = repository.get(session.session_id)
        assert before is not None
        with pytest.raises(SessionFinished):
            resolve.execute(session.session_id, WINNING[0])
    else:
        before = repository.get(session.session_id)
        assert before is not None
        with pytest.raises(TypeError):
            resolve.execute(session.session_id, None)  # type: ignore[arg-type]
    after = repository.get(session.session_id)
    assert before == after
