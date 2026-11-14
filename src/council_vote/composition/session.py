"""Wire session use cases to the SQLite repository."""

from dataclasses import dataclass

from council_vote.application.use_cases import ReadSession, ResolveAgenda, StartSession
from council_vote.infrastructure.repository import DjangoSessionRepository


@dataclass(frozen=True, slots=True)
class SessionUseCases:
    start: StartSession
    resolve: ResolveAgenda
    read: ReadSession


def build_session_use_cases() -> SessionUseCases:
    repository = DjangoSessionRepository()
    return SessionUseCases(
        start=StartSession(repository),
        resolve=ResolveAgenda(repository),
        read=ReadSession(repository),
    )
