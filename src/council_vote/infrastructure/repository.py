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
        raise ValueError("invalid persisted session history")
    return cast(dict[str, object], value)


def _sequence(value: object) -> list[object]:
    if not isinstance(value, list):
        raise ValueError("invalid persisted session history")
    return value


def _integer(value: object) -> int:
    if type(value) is not int:
        raise ValueError("invalid persisted session number")
    return value


def _text(value: object) -> str:
    if not isinstance(value, str):
        raise ValueError("invalid persisted session text")
    return value


def _boolean(value: object) -> bool:
    if type(value) is not bool:
        raise ValueError("invalid persisted session flag")
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
            outcome=Outcome(record.outcome) if record.outcome is not None else None,
            history=_decode_history(record.history),
        ),
    )


class DjangoSessionRepository(SessionRepository):
    @transaction.atomic
    def add(self, session: CouncilSession) -> None:
        SessionRecord.objects.create(
            session_id=session.session_id,
            council=session.council,
            attempts_left=session.attempts_left,
            outcome=session.outcome.value if session.outcome is not None else None,
            history=_encode_history(session),
            version=0,
        )

    def get(self, session_id: str) -> VersionedSession | None:
        try:
            record = SessionRecord.objects.get(session_id=session_id)
        except SessionRecord.DoesNotExist:
            return None
        return _snapshot(record)

    @transaction.atomic
    def save(self, snapshot: VersionedSession) -> bool:
        session = snapshot.session
        updated = SessionRecord.objects.filter(
            session_id=session.session_id, version=snapshot.version
        ).update(
            council=session.council,
            attempts_left=session.attempts_left,
            outcome=session.outcome.value if session.outcome is not None else None,
            history=_encode_history(session),
            version=F("version") + 1,
        )
        return updated == 1
