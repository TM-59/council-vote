"""Pure rules of the Council Session. No Django object is touched here."""

import copy
from itertools import product

import pytest

from council_vote.domain import (
    ATTEMPTS_PER_COUNCIL,
    COUNCILS,
    Agenda,
    AgendaResolved,
    Ballot,
    Clause,
    Council,
    CouncilSession,
    Outcome,
    Seat,
    SessionEnded,
    SessionFinished,
    Tally,
    VoteCounter,
)

Y, N, A = Ballot.YES, Ballot.NO, Ballot.ABSTAIN

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
def test_REQ_VOTE_quorum_and_strict_majority(
    ballots: tuple[Ballot, ...], quorum: bool, approved: bool
) -> None:
    tally = VoteCounter.tally(ballots)
    assert (tally.yes, tally.no, tally.abstain) == tuple(ballots.count(b) for b in (Y, N, A))
    assert tally.has_quorum is quorum
    assert tally.approved is approved


def test_REQ_VOTE_every_split_of_five_follows_the_rule() -> None:
    for ballots in product((Y, N, A), repeat=5):
        tally = VoteCounter.tally(ballots)
        yes, no = ballots.count(Y), ballots.count(N)
        assert tally.approved is (yes + no >= 3 and yes > no)
        assert tally.yes + tally.no + tally.abstain == 5


def test_REQ_VOTE_only_ballots_are_counted() -> None:
    with pytest.raises(TypeError):
        VoteCounter.tally([Y, "yes"])  # type: ignore[list-item]


def test_REQ_AGENDA_values_are_exact_and_immutable() -> None:
    agendas = Agenda.all()
    assert len(agendas) == len(set(agendas)) == 8
    agenda = Agenda(True, False, True)
    assert agenda.enabled(Clause.LAMPS) and not agenda.enabled(Clause.GATE)
    assert agenda == Agenda(True, False, True)
    with pytest.raises(AttributeError):
        agenda.lamps = False  # type: ignore[misc]
    for bad in (1, 0, "on", None):
        with pytest.raises(TypeError):
            Agenda(bad, False, False)  # type: ignore[arg-type]


def test_REQ_SEAT_public_condition_decides_one_ballot() -> None:
    seat = Seat("ferryman", ((Clause.GATE, True),), abstains_if=((Clause.BELL, True),))
    assert seat.vote(Agenda(False, True, False)) is Y
    assert seat.vote(Agenda(False, False, False)) is N
    assert seat.vote(Agenda(False, True, True)) is A  # abstaining comes first
    assert seat.condition() == "abstains if bell on; otherwise yes if gate on"
    assert Seat("clerk", ()).vote(Agenda(False, False, False)) is Y
    assert Seat("clerk", ()).condition() == "always yes"
    with pytest.raises(ValueError):
        Seat("", ())


def test_REQ_COUNCIL_five_distinct_seats() -> None:
    seat = Seat("a", ())
    with pytest.raises(ValueError):
        Council("short", (seat,) * 4)
    with pytest.raises(ValueError):
        Council("twins", (seat,) * 5)


def test_REQ_COUNCIL_fixed_councils_have_a_passing_agenda_but_not_every() -> None:
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
            if ballots.count(Y) + ballots.count(N) >= 3 and ballots.count(Y) > ballots.count(N):
                found.append(agenda)
        assert tuple(found) == expected
    assert Agenda(True, True, False) in passing[0]
    assert passing[1] == (Agenda(False, False, True), Agenda(True, False, True))
    assert passing[2] == (Agenda(False, True, True), Agenda(True, True, True))
    # no single agenda passes all three councils: the player must read each council
    assert not set(passing[0]) & set(passing[1]) & set(passing[2])


def test_REQ_COUNCIL_ballots_are_deterministic() -> None:
    for council in COUNCILS:
        for agenda in Agenda.all():
            assert council.ballots(agenda) == council.ballots(agenda)
            assert len(council.ballots(agenda)) == 5


WINNING = (Agenda(True, True, False), Agenda(False, False, True), Agenda(False, True, True))
REJECTED = Agenda(False, False, False)  # passes none of the three councils


def test_REQ_SESSION_three_approvals_win() -> None:
    session = CouncilSession("s1")
    assert (session.council, session.attempts_left, session.finished) == (
        0,
        ATTEMPTS_PER_COUNCIL,
        False,
    )
    events = session.resolve(WINNING[0])
    assert len(events) == 1 and isinstance(events[0], AgendaResolved) and events[0].approved
    assert (session.council, session.attempts_left) == (1, 2)
    session.resolve(WINNING[1])
    events = session.resolve(WINNING[2])
    assert events[-1] == SessionEnded(Outcome.WON)
    assert session.outcome is Outcome.WON and len(session.history) == 3
    assert [resolved.council for resolved in session.history] == [0, 1, 2]


def test_REQ_SESSION_a_rejection_costs_an_attempt_and_approval_restores_them() -> None:
    session = CouncilSession("s2")
    (resolved,) = session.resolve(REJECTED)
    assert isinstance(resolved, AgendaResolved) and not resolved.approved
    assert resolved.tally == Tally(yes=1, no=3, abstain=1)
    assert (session.council, session.attempts_left, session.finished) == (0, 1, False)
    session.resolve(WINNING[0])
    assert (session.council, session.attempts_left) == (1, 2)


def test_REQ_SESSION_two_rejections_lose_and_repeats_are_allowed() -> None:
    session = CouncilSession("s3")
    session.resolve(REJECTED)
    events = session.resolve(REJECTED)  # the same agenda again consumes another attempt
    assert events[-1] == SessionEnded(Outcome.LOST)
    assert session.outcome is Outcome.LOST and session.attempts_left == 0
    assert len(session.history) == 2


def test_REQ_SESSION_losing_at_the_last_council() -> None:
    session = CouncilSession("s4")
    session.resolve(WINNING[0])
    session.resolve(WINNING[1])
    session.resolve(REJECTED)
    assert session.resolve(REJECTED)[-1] == SessionEnded(Outcome.LOST)
    assert session.council == 2


@pytest.mark.parametrize("finish", [Outcome.WON, Outcome.LOST])
def test_REQ_SESSION_finished_sessions_reject_and_do_not_change(finish: Outcome) -> None:
    session = CouncilSession("s5")
    for agenda in WINNING if finish is Outcome.WON else (REJECTED, REJECTED):
        session.resolve(agenda)
    assert session.outcome is finish
    before = copy.deepcopy(session)
    with pytest.raises(SessionFinished):
        session.resolve(WINNING[0])
    assert session == before


@pytest.mark.parametrize("bad", [None, "lamps", (True, True, True), 7])
def test_REQ_SESSION_invalid_agenda_changes_nothing(bad: object) -> None:
    session = CouncilSession("s6")
    session.resolve(REJECTED)
    before = copy.deepcopy(session)
    with pytest.raises(TypeError):
        session.resolve(bad)  # type: ignore[arg-type]
    assert session == before


def test_REQ_SESSION_identity_is_required_and_history_records_the_ballots() -> None:
    with pytest.raises(ValueError):
        CouncilSession("")
    with pytest.raises(ValueError):
        CouncilSession("s", councils=())
    session = CouncilSession("s7")
    (resolved,) = session.resolve(WINNING[0])
    assert isinstance(resolved, AgendaResolved)
    assert resolved.ballots == (Y, Y, Y, Y, Y) and resolved.agenda == WINNING[0]
    assert session.history == (resolved,)


def test_REQ_SESSION_every_pair_of_first_moves_is_reproducible() -> None:
    for first, second in product(Agenda.all(), repeat=2):
        runs = []
        for _ in range(2):
            session = CouncilSession("replay")
            session.resolve(first)
            if not session.finished:
                session.resolve(second)
            runs.append((session.council, session.attempts_left, session.outcome, session.history))
        assert runs[0] == runs[1]
