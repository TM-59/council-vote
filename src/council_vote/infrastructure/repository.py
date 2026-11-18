"""Django ORM adapter for the application session repository port."""

from typing import cast

from django.db import transaction
from django.db.models import F

from council_vote.application.ports import SessionRepository, VersionedSession
from council_vote.domain import (
    Agenda,
    AgendaResolved,
    Ballot,
    CouncilSession,
    Outcome,
    Tally,
)

from .models import SessionRecord

HISTORY = "history"
NUMBER = "number"
TEXT = "text"
FLAG = "flag"


class PersistedSessionError(TypeError, ValueError):
    """A stored session record does not have the shape the repository wrote.

    It is a ValueError (the stored value is wrong) and a TypeError (the value has the
    wrong type), so callers that caught either keep working.
    """

    def __init__(self, what: str) -> None:
        """Name the part of the record that is invalid."""
        super().__init__(f"invalid persisted session {what}")


def _encode_history(session: CouncilSession) -> list[dict[str, object]]:
    return [
        {
            "council": event.council,
            "agenda": {
                "lamps": event.agenda.lamps,
                "gate": event.agenda.gate,
                "bell": event.agenda.bell,
            },
            "ballots": [ballot.value for ballot in event.ballots],
            "tally": {
                "yes": event.tally.yes,
                "no": event.tally.no,
                "abstain": event.tally.abstain,
            },
            "approved": event.approved,
        }
        for event in session.history
    ]


def _mapping(value: object) -> dict[str, object]:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise PersistedSessionError(HISTORY)
    return cast("dict[str, object]", value)


def _sequence(value: object) -> list[object]:
    if not isinstance(value, list):
        raise PersistedSessionError(HISTORY)
    return value


def _integer(value: object) -> int:
    if type(value) is not int:
        raise PersistedSessionError(NUMBER)
    return value


def _text(value: object) -> str:
    if not isinstance(value, str):
        raise PersistedSessionError(TEXT)
    return value


def _boolean(value: object) -> bool:
    if type(value) is not bool:
        raise PersistedSessionError(FLAG)
    return value


def _decode_history(value: object) -> tuple[AgendaResolved, ...]:
    events: list[AgendaResolved] = []
    for raw_event in _sequence(value):
        event = _mapping(raw_event)
        raw_agenda = _mapping(event.get("agenda"))
        raw_tally = _mapping(event.get("tally"))
        ballots = tuple(Ballot(_text(ballot)) for ballot in _sequence(event.get("ballots")))
        events.append(
            AgendaResolved(
                council=_integer(event.get("council")),
                agenda=Agenda(
                    lamps=_boolean(raw_agenda.get("lamps")),
                    gate=_boolean(raw_agenda.get("gate")),
                    bell=_boolean(raw_agenda.get("bell")),
                ),
                ballots=ballots,
                tally=Tally(
                    yes=_integer(raw_tally.get("yes")),
                    no=_integer(raw_tally.get("no")),
                    abstain=_integer(raw_tally.get("abstain")),
                ),
                approved=_boolean(event.get("approved")),
            )
        )
    return tuple(events)


def _snapshot(record: SessionRecord) -> VersionedSession:
    return VersionedSession(
        version=record.version,
        session=CouncilSession(
            session_id=record.session_id,
            council=record.council,
            attempts_left=record.attempts_left,
            outcome=Outcome(record.outcome) if record.outcome else None,
            history=_decode_history(record.history),
        ),
    )


class DjangoSessionRepository(SessionRepository):
    """Session repository on the Django ORM, with optimistic versioning."""

    @transaction.atomic
    def add(self, session: CouncilSession) -> None:
        """Insert the session as a new record at version 0."""
        SessionRecord.objects.create(
            session_id=session.session_id,
            council=session.council,
            attempts_left=session.attempts_left,
            outcome=session.outcome.value if session.outcome is not None else "",
            history=_encode_history(session),
            version=0,
        )

    def get(self, session_id: str) -> VersionedSession | None:
        """Return the stored session and its version, or None."""
        try:
            record = SessionRecord.objects.get(session_id=session_id)
        except SessionRecord.DoesNotExist:
            return None
        return _snapshot(record)

    @transaction.atomic
    def save(self, snapshot: VersionedSession) -> bool:
        """Update the record only if its version is unchanged; return whether it was."""
        session = snapshot.session
        updated = SessionRecord.objects.filter(
            session_id=session.session_id, version=snapshot.version
        ).update(
            council=session.council,
            attempts_left=session.attempts_left,
            outcome=session.outcome.value if session.outcome is not None else "",
            history=_encode_history(session),
            version=F("version") + 1,
        )
        return updated == 1
