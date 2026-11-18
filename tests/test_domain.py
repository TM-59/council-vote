"""Pure rules of the Council Session. No Django object is touched here."""

import copy
from itertools import product
from typing import cast

import pytest

from council_vote.domain import (
    ATTEMPTS_PER_COUNCIL,
    COUNCILS,
    QUORUM,
    SEATS_PER_COUNCIL,
    Agenda,
    AgendaResolved,
    Ballot,
    Clause,
    ClauseValueError,
    Council,
    CouncilSession,
    CouncilShapeError,
    MissingIdentityError,
    NotABallotError,
    NotAnAgendaError,
    Outcome,
    Seat,
    SessionEnded,
    SessionFinishedError,
    Tally,
    VoteCounter,
)

Y, N, A = Ballot.YES, Ballot.NO, Ballot.ABSTAIN
AGENDA_COUNT = 2**3  # three clauses, each on or off

# Independent table: ballots -> (quorum, approved). Written by hand, not derived from the code.
COUNTING = [
    ((Y, Y, Y, N, A), True, True),  # four take part, three to one
    ((Y, Y, A, A, A), False, False),  # two yes, three abstain: no quorum
    ((Y, Y, N, N, A), True, False),  # a tie is rejected
    ((Y, Y, Y, Y, Y), True, True),
    ((N, N, N, N, N), True, False),
    ((A, A, A, A, A), False, False),
    ((Y, Y, N, A, A), True, True),  # exactly three take part
    ((Y, N, N, A, A), True, False),
    ((Y, Y, Y, A, A), True, True),
    ((Y, A, A, A, A), False, False),
]


@pytest.mark.parametrize(("ballots", "quorum", "approved"), COUNTING)
def test_req_vote_quorum_and_strict_majority(
    ballots: tuple[Ballot, ...], *, quorum: bool, approved: bool
) -> None:
    """REQ-VOTE: the hand-written table of quorum and majority holds."""
    tally = VoteCounter.tally(ballots)
    assert (tally.yes, tally.no, tally.abstain) == tuple(ballots.count(b) for b in (Y, N, A))
    assert tally.has_quorum is quorum
    assert tally.approved is approved


def test_req_vote_every_split_of_five_follows_the_rule() -> None:
    """REQ-VOTE: all 243 ordered ballots follow quorum and strict majority."""
    for ballots in product((Y, N, A), repeat=5):
        tally = VoteCounter.tally(ballots)
        yes, no = ballots.count(Y), ballots.count(N)
        assert tally.approved is (yes + no >= QUORUM and yes > no)
        assert tally.yes + tally.no + tally.abstain == SEATS_PER_COUNCIL


def test_req_vote_only_ballots_are_counted() -> None:
    """REQ-VOTE: the counter refuses values that are not ballots."""
    with pytest.raises(NotABallotError):
        VoteCounter.tally(cast("list[Ballot]", [Y, "yes"]))


def test_req_agenda_values_are_exact_and_immutable() -> None:
    """REQ-AGENDA: eight distinct agendas, frozen, with boolean clauses only."""
    agendas = Agenda.all()
    assert len(agendas) == len(set(agendas)) == AGENDA_COUNT
    agenda = Agenda(lamps=True, gate=False, bell=True)
    assert agenda.enabled(Clause.LAMPS)
    assert not agenda.enabled(Clause.GATE)
    assert agenda == Agenda(lamps=True, gate=False, bell=True)
    clause = "lamps"
    with pytest.raises(AttributeError):
        setattr(agenda, clause, False)  # a frozen value cannot be reassigned
    for bad in (1, 0, "on", None):
        with pytest.raises(ClauseValueError):
            Agenda(lamps=cast("bool", bad), gate=False, bell=False)


def test_req_seat_public_condition_decides_one_ballot() -> None:
    """REQ-SEAT: a seat's public condition decides its single ballot."""
    seat = Seat("ferryman", ((Clause.GATE, True),), abstains_if=((Clause.BELL, True),))
    assert seat.vote(Agenda(lamps=False, gate=True, bell=False)) is Y
    assert seat.vote(Agenda(lamps=False, gate=False, bell=False)) is N
    assert seat.vote(Agenda(lamps=False, gate=True, bell=True)) is A  # abstaining comes first
    assert seat.condition() == "abstains if bell on; otherwise yes if gate on"
    assert Seat("clerk", ()).vote(Agenda(lamps=False, gate=False, bell=False)) is Y
    assert Seat("clerk", ()).condition() == "always yes"
    with pytest.raises(MissingIdentityError):
        Seat("", ())


def test_req_council_five_distinct_seats() -> None:
    """REQ-COUNCIL: a council has exactly five distinct seats."""
    seat = Seat("a", ())
    with pytest.raises(CouncilShapeError):
        Council("short", (seat,) * (SEATS_PER_COUNCIL - 1))
    with pytest.raises(CouncilShapeError):
        Council("twins", (seat,) * SEATS_PER_COUNCIL)


def test_req_council_fixed_councils_have_a_passing_agenda_but_not_every() -> None:
    """REQ-COUNCIL: each fixed council passes some agendas and none passes all three."""
    assert [council.name for council in COUNCILS] == [
        "Harbour Wardens",
        "Night Watch",
        "Guild Elders",
    ]
    passing = [council.passing_agendas() for council in COUNCILS]
    assert [len(agendas) for agendas in passing] == [3, 2, 2]
    # enumerated independently of passing_agendas()
    for council, expected in zip(COUNCILS, passing, strict=True):
        found = []
        for agenda in Agenda.all():
            ballots = [seat.vote(agenda) for seat in council.seats]
            if ballots.count(Y) + ballots.count(N) >= QUORUM and ballots.count(Y) > ballots.count(
                N
            ):
                found.append(agenda)
        assert tuple(found) == expected
    assert Agenda(lamps=True, gate=True, bell=False) in passing[0]
    assert passing[1] == (
        Agenda(lamps=False, gate=False, bell=True),
        Agenda(lamps=True, gate=False, bell=True),
    )
    assert passing[2] == (
        Agenda(lamps=False, gate=True, bell=True),
        Agenda(lamps=True, gate=True, bell=True),
    )
    # no single agenda passes all three councils: the player must read each council
    assert not set(passing[0]) & set(passing[1]) & set(passing[2])


def test_req_council_ballots_are_deterministic() -> None:
    """REQ-COUNCIL: the same agenda always gets the same five ballots."""
    for council in COUNCILS:
        for agenda in Agenda.all():
            assert council.ballots(agenda) == council.ballots(agenda)
            assert len(council.ballots(agenda)) == SEATS_PER_COUNCIL


WINNING = (
    Agenda(lamps=True, gate=True, bell=False),
    Agenda(lamps=False, gate=False, bell=True),
    Agenda(lamps=False, gate=True, bell=True),
)
REJECTED = Agenda(lamps=False, gate=False, bell=False)  # passes none of the three councils


def test_req_session_three_approvals_win() -> None:
    """REQ-SESSION: three approvals in a row win the session."""
    session = CouncilSession("s1")
    assert (session.council, session.attempts_left, session.finished) == (
        0,
        ATTEMPTS_PER_COUNCIL,
        False,
    )
    events = session.resolve(WINNING[0])
    assert len(events) == 1
    assert isinstance(events[0], AgendaResolved)
    assert events[0].approved
    assert (session.council, session.attempts_left) == (1, 2)
    session.resolve(WINNING[1])
    events = session.resolve(WINNING[2])
    assert events[-1] == SessionEnded(Outcome.WON)
    assert session.outcome is Outcome.WON
    assert len(session.history) == len(COUNCILS)
    assert [resolved.council for resolved in session.history] == [0, 1, 2]


def test_req_session_a_rejection_costs_an_attempt_and_approval_restores_them() -> None:
    """REQ-SESSION: a rejection costs an attempt; moving on restores them."""
    session = CouncilSession("s2")
    (resolved,) = session.resolve(REJECTED)
    assert isinstance(resolved, AgendaResolved)
    assert not resolved.approved
    assert resolved.tally == Tally(yes=1, no=3, abstain=1)
    assert (session.council, session.attempts_left, session.finished) == (0, 1, False)
    session.resolve(WINNING[0])
    assert (session.council, session.attempts_left) == (1, 2)


def test_req_session_two_rejections_lose_and_repeats_are_allowed() -> None:
    """REQ-SESSION: two rejections at one council lose; repeating an agenda is allowed."""
    session = CouncilSession("s3")
    session.resolve(REJECTED)
    events = session.resolve(REJECTED)  # the same agenda again consumes another attempt
    assert events[-1] == SessionEnded(Outcome.LOST)
    assert session.outcome is Outcome.LOST
    assert session.attempts_left == 0
    assert len(session.history) == ATTEMPTS_PER_COUNCIL


def test_req_session_losing_at_the_last_council() -> None:
    """REQ-SESSION: the session can be lost at the last council."""
    session = CouncilSession("s4")
    session.resolve(WINNING[0])
    session.resolve(WINNING[1])
    session.resolve(REJECTED)
    assert session.resolve(REJECTED)[-1] == SessionEnded(Outcome.LOST)
    assert session.council == len(COUNCILS) - 1


@pytest.mark.parametrize("finish", [Outcome.WON, Outcome.LOST])
def test_req_session_finished_sessions_reject_and_do_not_change(finish: Outcome) -> None:
    """REQ-SESSION: a finished session refuses agendas and stays unchanged."""
    session = CouncilSession("s5")
    for agenda in WINNING if finish is Outcome.WON else (REJECTED, REJECTED):
        session.resolve(agenda)
    assert session.outcome is finish
    before = copy.deepcopy(session)
    with pytest.raises(SessionFinishedError):
        session.resolve(WINNING[0])
    assert session == before


@pytest.mark.parametrize("bad", [None, "lamps", (True, True, True), 7])
def test_req_session_invalid_agenda_changes_nothing(bad: object) -> None:
    """REQ-SESSION: a proposal that is not an Agenda changes nothing."""
    session = CouncilSession("s6")
    session.resolve(REJECTED)
    before = copy.deepcopy(session)
    with pytest.raises(NotAnAgendaError):
        session.resolve(cast("Agenda", bad))
    assert session == before


def test_req_session_identity_is_required_and_history_records_the_ballots() -> None:
    """REQ-SESSION: identity and councils are required; history records each ballot."""
    with pytest.raises(MissingIdentityError):
        CouncilSession("")
    with pytest.raises(CouncilShapeError):
        CouncilSession("s", councils=())
    session = CouncilSession("s7")
    (resolved,) = session.resolve(WINNING[0])
    assert isinstance(resolved, AgendaResolved)
    assert resolved.ballots == (Y, Y, Y, Y, Y)
    assert resolved.agenda == WINNING[0]
    assert session.history == (resolved,)


def test_req_session_every_pair_of_first_moves_is_reproducible() -> None:
    """REQ-SESSION: every pair of first moves replays to the same state."""
    for first, second in product(Agenda.all(), repeat=2):
        runs = []
        for _ in range(2):
            session = CouncilSession("replay")
            session.resolve(first)
            if not session.finished:
                session.resolve(second)
            runs.append((session.council, session.attempts_left, session.outcome, session.history))
        assert runs[0] == runs[1]
