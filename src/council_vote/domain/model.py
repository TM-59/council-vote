"""Council Session: values, the aggregate, its events and the counting rule.

Standard library only. Nothing here knows about Django, storage or the screen.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from enum import Enum

QUORUM = 3
ATTEMPTS_PER_COUNCIL = 2


class Clause(Enum):
    LAMPS = "lamps"
    GATE = "gate"
    BELL = "bell"


class Ballot(Enum):
    YES = "yes"
    NO = "no"
    ABSTAIN = "abstain"


class Outcome(Enum):
    WON = "won"
    LOST = "lost"


class SessionFinished(Exception):
    """A finished session accepts no further agenda."""


@dataclass(frozen=True, slots=True)
class Agenda:
    """The three clauses, each enabled or disabled: eight possible agendas."""

    lamps: bool
    gate: bool
    bell: bool

    def __post_init__(self) -> None:
        for name in ("lamps", "gate", "bell"):
            if type(getattr(self, name)) is not bool:
                raise TypeError(f"clause {name} must be True or False")

    def enabled(self, clause: Clause) -> bool:
        return bool(getattr(self, clause.value))

    @staticmethod
    def all() -> tuple[Agenda, ...]:
        flags = (False, True)
        return tuple(
            Agenda(lamps, gate, bell) for lamps in flags for gate in flags for bell in flags
        )


# A requirement is a conjunction of clause states; the empty requirement always holds.
Requirement = tuple[tuple[Clause, bool], ...]


def holds(requirement: Requirement, agenda: Agenda) -> bool:
    return all(agenda.enabled(clause) is state for clause, state in requirement)


@dataclass(frozen=True, slots=True)
class Seat:
    """A council member with a public voting condition.

    The seat abstains when `abstains_if` holds; otherwise it votes yes when `yes_if`
    holds, and no when it does not.
    """

    seat_id: str
    yes_if: Requirement
    abstains_if: Requirement | None = None

    def __post_init__(self) -> None:
        if not self.seat_id:
            raise ValueError("a seat needs an identity")

    def vote(self, agenda: Agenda) -> Ballot:
        if self.abstains_if is not None and holds(self.abstains_if, agenda):
            return Ballot.ABSTAIN
        return Ballot.YES if holds(self.yes_if, agenda) else Ballot.NO

    def condition(self) -> str:
        """The public condition in words, as the screen will show it."""

        def words(requirement: Requirement) -> str:
            return " and ".join(f"{c.value} {'on' if s else 'off'}" for c, s in requirement)

        text = f"yes if {words(self.yes_if)}" if self.yes_if else "always yes"
        if self.abstains_if is not None:
            text = f"abstains if {words(self.abstains_if)}; otherwise {text}"
        return text


@dataclass(frozen=True, slots=True)
class Tally:
    yes: int
    no: int
    abstain: int

    @property
    def participating(self) -> int:
        return self.yes + self.no

    @property
    def has_quorum(self) -> bool:
        return self.participating >= QUORUM

    @property
    def approved(self) -> bool:
        return self.has_quorum and self.yes > self.no


class VoteCounter:
    """Pure domain service: count ballots; quorum and strict majority decide."""

    @staticmethod
    def tally(ballots: Iterable[Ballot]) -> Tally:
        cast = tuple(ballots)
        if any(not isinstance(ballot, Ballot) for ballot in cast):
            raise TypeError("only ballots can be counted")
        return Tally(
            yes=sum(ballot is Ballot.YES for ballot in cast),
            no=sum(ballot is Ballot.NO for ballot in cast),
            abstain=sum(ballot is Ballot.ABSTAIN for ballot in cast),
        )


@dataclass(frozen=True, slots=True)
class Council:
    """Five seats with public conditions; ballots follow from them and the agenda alone."""

    name: str
    seats: tuple[Seat, ...]

    def __post_init__(self) -> None:
        if len(self.seats) != 5 or len({seat.seat_id for seat in self.seats}) != 5:
            raise ValueError("a council has five distinct seats")

    def ballots(self, agenda: Agenda) -> tuple[Ballot, ...]:
        return tuple(seat.vote(agenda) for seat in self.seats)

    def passing_agendas(self) -> tuple[Agenda, ...]:
        return tuple(a for a in Agenda.all() if VoteCounter.tally(self.ballots(a)).approved)


@dataclass(frozen=True, slots=True)
class AgendaResolved:
    council: int
    agenda: Agenda
    ballots: tuple[Ballot, ...]
    tally: Tally
    approved: bool


@dataclass(frozen=True, slots=True)
class SessionEnded:
    outcome: Outcome


Event = AgendaResolved | SessionEnded


def _on(*clauses: Clause) -> Requirement:
    return tuple((clause, True) for clause in clauses)


def _off(*clauses: Clause) -> Requirement:
    return tuple((clause, False) for clause in clauses)


L, G, B = Clause.LAMPS, Clause.GATE, Clause.BELL

# The three fixed councils. Every condition is public; nothing is random.
COUNCILS: tuple[Council, ...] = (
    Council(
        "Harbour Wardens",
        (
            Seat("warden", _on(L)),
            Seat("pilot", _on(L, G)),
            Seat("chandler", _off(B)),
            Seat("ferryman", _on(G), abstains_if=_on(B)),
            Seat("clerk", (), abstains_if=_off(L)),
        ),
    ),
    Council(
        "Night Watch",
        (
            Seat("captain", _on(B) + _off(G)),
            Seat("lamplighter", _on(L), abstains_if=_off(L, B)),
            Seat("gatekeeper", _off(G)),
            Seat("ringer", _on(B), abstains_if=_on(G) + _off(B)),
            Seat("recruit", _off(L), abstains_if=_on(L, G)),
        ),
    ),
    Council(
        "Guild Elders",
        (
            Seat("mason", _on(G) + _off(L)),
            Seat("weaver", _on(L) + _off(B), abstains_if=_on(L, B)),
            Seat("smith", _on(B), abstains_if=_off(G, B)),
            Seat("scribe", _off(L, G), abstains_if=_on(G, B)),
            Seat("elder", _on(G, B)),
        ),
    ),
)


@dataclass(slots=True)
class CouncilSession:
    """Aggregate: which council is sitting, attempts left, and everything resolved so far."""

    session_id: str
    councils: tuple[Council, ...] = COUNCILS
    council: int = 0
    attempts_left: int = ATTEMPTS_PER_COUNCIL
    outcome: Outcome | None = None
    history: tuple[AgendaResolved, ...] = field(default=())

    def __post_init__(self) -> None:
        if not self.session_id:
            raise ValueError("a session needs an identity")
        if not self.councils:
            raise ValueError("a session needs at least one council")

    @property
    def finished(self) -> bool:
        return self.outcome is not None

    def resolve(self, agenda: Agenda) -> tuple[Event, ...]:
        """Put an agenda to the sitting council. Returns the events that happened.

        Nothing changes when the session is finished or the agenda is not an Agenda.
        """
        if self.finished:
            raise SessionFinished("the session is over")
        if not isinstance(agenda, Agenda):
            raise TypeError("an agenda of three clauses is required")
        sitting = self.councils[self.council]
        ballots = sitting.ballots(agenda)
        tally = VoteCounter.tally(ballots)
        resolved = AgendaResolved(self.council, agenda, ballots, tally, tally.approved)
        events: list[Event] = [resolved]
        self.history += (resolved,)
        if tally.approved:
            if self.council + 1 == len(self.councils):
                self.outcome = Outcome.WON
            else:
                self.council += 1
                self.attempts_left = ATTEMPTS_PER_COUNCIL
        else:
            self.attempts_left -= 1
            if self.attempts_left == 0:
                self.outcome = Outcome.LOST
        if self.outcome is not None:
            events.append(SessionEnded(self.outcome))
        return tuple(events)
