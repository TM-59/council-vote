"""Regenerates the drawn figures and the measured-values table of docs/theory.

Run with `make theory-figs`. Everything is computed by the domain itself
(src/council_vote/domain); nothing here changes it. Standard library only.
"""

from __future__ import annotations

import sys
from collections import Counter
from itertools import product
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from council_vote.domain import (  # noqa: E402
    ATTEMPTS_PER_COUNCIL,
    COUNCILS,
    QUORUM,
    Agenda,
    Ballot,
    Council,
    CouncilSession,
    Outcome,
    SessionFinished,
    Tally,
    VoteCounter,
)

OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "docs/theory/figures"
ROWS: list[str] = []
COLOUR = {Ballot.YES: "#2ca02c", Ballot.NO: "#d62728", Ballot.ABSTAIN: "#bbbbbb"}
LETTER = {Ballot.YES: "yes", Ballot.NO: "no", Ballot.ABSTAIN: "–"}


def value(key: str, what: str, measured: float, theory: float) -> None:
    """One row of the table: id | what | measured | theory | error (absolute when theory is 0)."""
    error = abs(measured / theory - 1) if theory else abs(measured - theory)
    ROWS.append(f"| `{key}` | {what} | {measured:.8g} | {theory:.8g} | {error:.2e} |")


def svg(name: str, width: int, height: int, body: list[str]) -> None:
    head = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" '
        f'height="{height}" font-family="sans-serif" font-size="12">'
    )
    text = "\n".join(
        [head, f'<rect width="{width}" height="{height}" fill="#ffffff"/>', *body, "</svg>"]
    )
    (OUT / name).write_text(text + "\n", encoding="utf-8")


def label(agenda: Agenda) -> str:
    on = [name for name in ("lamps", "gate", "bell") if getattr(agenda, name)]
    return " + ".join(on) if on else "nothing"


def board(name: str, council: Council) -> None:
    """One council as a board: a row per agenda, a cell per seat, the tally and the result."""
    left, top, cell_w, cell_h = 150, 70, 92, 26
    width, height = left + 5 * cell_w + 190, top + 8 * cell_h + 20
    out = [
        f'<text x="16" y="26" font-size="16" font-weight="bold" fill="#222">{council.name}: every agenda</text>'
    ]
    out.append(f'<text x="16" y="{top - 10}" fill="#444">clauses switched on</text>')
    for i, seat in enumerate(council.seats):
        out.append(
            f'<text x="{left + i * cell_w + cell_w / 2:.0f}" y="{top - 10}" text-anchor="middle" fill="#222">{seat.seat_id}</text>'
        )
    out.append(
        f'<text x="{left + 5 * cell_w + 12}" y="{top - 10}" fill="#444">yes / no / abstain</text>'
    )
    for row, agenda in enumerate(Agenda.all()):
        y = top + row * cell_h
        ballots = council.ballots(agenda)
        tally = VoteCounter.tally(ballots)
        out.append(f'<text x="16" y="{y + 17}" fill="#222">{label(agenda)}</text>')
        for i, ballot in enumerate(ballots):
            out.append(
                f'<rect x="{left + i * cell_w}" y="{y}" width="{cell_w - 3}" height="{cell_h - 3}" fill="{COLOUR[ballot]}"/>'
            )
            out.append(
                f'<text x="{left + i * cell_w + cell_w / 2:.0f}" y="{y + 17}" text-anchor="middle" fill="#ffffff">{LETTER[ballot]}</text>'
            )
        verdict = (
            "PASSES" if tally.approved else "no quorum" if not tally.has_quorum else "rejected"
        )
        weight = ' font-weight="bold"' if tally.approved else ""
        out.append(
            f'<text x="{left + 5 * cell_w + 12}" y="{y + 17}" fill="#222"{weight}>{tally.yes} / {tally.no} / {tally.abstain}   {verdict}</text>'
        )
    svg(name, width, height, out)


def counting_grid() -> None:
    """Every split of five ballots: yes across, no down; green where the agenda is approved."""
    left, top, cell = 90, 70, 64
    out = [
        '<text x="16" y="26" font-size="16" font-weight="bold" fill="#222">Five ballots: when is an agenda approved?</text>'
    ]
    out.append(
        f'<text x="{left + 3 * cell}" y="{top - 28}" text-anchor="middle" fill="#222">yes ballots</text>'
    )
    out.append(
        f'<text transform="translate(22 {top + 3 * cell}) rotate(-90)" text-anchor="middle" fill="#222">no ballots</text>'
    )
    for yes in range(6):
        out.append(
            f'<text x="{left + yes * cell + cell / 2:.0f}" y="{top - 8}" text-anchor="middle" fill="#444">{yes}</text>'
        )
    for no in range(6):
        out.append(
            f'<text x="{left - 10}" y="{top + no * cell + cell / 2 + 4:.0f}" text-anchor="end" fill="#444">{no}</text>'
        )
        for yes in range(6 - no):
            tally = Tally(yes, no, 5 - yes - no)
            fill = "#2ca02c" if tally.approved else "#bbbbbb" if not tally.has_quorum else "#d62728"
            text = (
                "approved"
                if tally.approved
                else "no quorum"
                if not tally.has_quorum
                else "rejected"
            )
            x, y = left + yes * cell, top + no * cell
            out.append(
                f'<rect x="{x}" y="{y}" width="{cell - 3}" height="{cell - 3}" fill="{fill}"/>'
            )
            out.append(
                f'<text x="{x + cell / 2 - 1:.0f}" y="{y + cell / 2 - 2:.0f}" text-anchor="middle" fill="#ffffff" font-size="11">{text}</text>'
            )
            out.append(
                f'<text x="{x + cell / 2 - 1:.0f}" y="{y + cell / 2 + 13:.0f}" text-anchor="middle" fill="#ffffff" font-size="11">{5 - yes - no} abstain</text>'
            )
    svg("counting.svg", left + 6 * cell + 20, top + 6 * cell + 16, out)


def bars(name: str, title: str, labels: list[str], heights: list[int]) -> None:
    width, height, left, top, plot_w, plot_h = 720, 360, 70, 44, 630, 250
    peak = (max(heights) or 1) * 1.1
    step = plot_w / len(heights)
    out = [f'<text x="{left}" y="26" font-size="16" font-weight="bold" fill="#222">{title}</text>']
    for i, (text, h) in enumerate(zip(labels, heights, strict=True)):
        bar_h = h / peak * plot_h
        x = left + i * step + step * 0.15
        out.append(
            f'<rect x="{x:.1f}" y="{top + plot_h - bar_h:.1f}" width="{step * 0.7:.1f}" height="{bar_h:.1f}" fill="#1f77b4"/>'
        )
        middle = left + i * step + step / 2
        out.append(
            f'<text x="{middle:.1f}" y="{top + plot_h - bar_h - 4:.1f}" text-anchor="middle" fill="#222">{h}</text>'
        )
        out.append(
            f'<text x="{middle:.1f}" y="{top + plot_h + 18}" text-anchor="middle" fill="#444">{text}</text>'
        )
    out.append(
        f'<rect x="{left}" y="{top}" width="{plot_w}" height="{plot_h}" fill="none" stroke="#888"/>'
    )
    svg(name, width, height, out)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    agendas = Agenda.all()

    # S02: agendas
    value("agendas", "different agendas, enumerated (theory 2^3)", len(set(agendas)), 8)
    refused = 0
    for bad in (1, 0, "on", None):
        try:
            Agenda(bad, False, False)  # type: ignore[arg-type]
        except TypeError:
            refused += 1
    value(
        "agenda-rejected",
        "of four non-boolean clause values, how many raise TypeError (theory 4)",
        refused,
        4,
    )

    # S03: seats
    seats = [seat for council in COUNCILS for seat in council.seats]
    value("seats", "seats in the three fixed councils (theory 15)", len(seats), 15)
    one_each = all(isinstance(seat.vote(agenda), Ballot) for seat in seats for agenda in agendas)
    value(
        "seat-one-ballot",
        "every seat gives exactly one ballot for every agenda, 15 x 8 cases (1 = yes)",
        one_each,
        1,
    )
    abstainers = sum(seat.abstains_if is not None for seat in seats)
    value("seat-abstainers", "seats that have an abstaining condition", abstainers, 0)
    first = 0
    for seat in seats:
        for agenda in agendas:
            if seat.abstains_if is not None and all(
                agenda.enabled(c) is s for c, s in seat.abstains_if
            ):
                first += seat.vote(agenda) is not Ballot.ABSTAIN
    value(
        "seat-abstain-first",
        "cases where the abstaining condition holds but the ballot is not an abstention (theory 0)",
        first,
        0,
    )

    # S04: counting
    counting_grid()
    wrong = 0
    approved = 0
    splits = 0
    for ballots in product(Ballot, repeat=5):
        splits += 1
        tally = VoteCounter.tally(ballots)
        yes, no = ballots.count(Ballot.YES), ballots.count(Ballot.NO)
        wrong += tally.approved is not (yes + no >= QUORUM and yes > no)
        approved += tally.approved
    value("count-splits", "ordered ways five seats can vote, enumerated (theory 3^5)", splits, 243)
    value(
        "count-rule",
        "of them, cases where the counter disagrees with 'at least three take part and yes exceeds no' (theory 0)",
        wrong,
        0,
    )
    value("count-approved", "of them, cases that approve the agenda", approved, 0)
    value(
        "count-tie",
        "approved for two yes, two no, one abstention (theory 0: a tie is rejected)",
        Tally(2, 2, 1).approved,
        0,
    )
    value(
        "count-no-quorum",
        "approved for two yes, three abstentions (theory 0: no quorum)",
        Tally(2, 0, 3).approved,
        0,
    )
    value(
        "count-three-one",
        "approved for three yes, one no, one abstention (theory 1)",
        Tally(3, 1, 1).approved,
        1,
    )

    # S05: the three councils
    passing = []
    for i, council in enumerate(COUNCILS, 1):
        board(f"council-{i}.svg", council)
        passing.append(council.passing_agendas())
        value(
            f"council-{i}-passing",
            f"agendas of eight that pass council {i}, {council.name}",
            len(passing[-1]),
            0,
        )
    everywhere = set(passing[0]) & set(passing[1]) & set(passing[2])
    value(
        "council-common",
        "agendas that pass all three councils (theory 0: each council must be read)",
        len(everywhere),
        0,
    )

    # S06, S08: every way to play
    results: Counter[str] = Counter()
    plans = 0
    finished = 0
    for plan in product(agendas, repeat=6):  # at most two attempts at each of three councils
        plans += 1
        session = CouncilSession("all")
        for agenda in plan:
            if session.finished:
                break
            session.resolve(agenda)
        finished += session.finished
        key = "won" if session.outcome is Outcome.WON else f"lost at council {session.council + 1}"
        results[key] += 1
    labels = ["lost at council 1", "lost at council 2", "lost at council 3", "won"]
    bars(
        "random-play.svg",
        "All 262144 plans of six agendas: how the session ends",
        labels,
        [results[k] for k in labels],
    )
    p = [len(agendas_) / 8 for agendas_ in passing]
    chance = 1.0
    for q in p:
        chance *= 1 - (1 - q) ** ATTEMPTS_PER_COUNCIL
    for i, key in enumerate(labels[:3], 1):
        value(f"play-lost-{i}", f"plans that end {key}", results[key], 0)
    value("play-won", "plans that win", results["won"], 0)
    value(
        "play-plans", "plans of six agendas played through the aggregate (theory 8^6)", plans, 8**6
    )
    value(
        "play-all-finish",
        "of them, plans after which the session is finished (theory all: six agendas always suffice)",
        finished,
        8**6,
    )
    value(
        "play-win-chance",
        "fraction of plans that win: the chance of winning by picking agendas at random (theory: product over councils of 1 - (1 - p)^2)",
        results["won"] / plans,
        chance,
    )
    best = CouncilSession("best")
    for agendas_ in passing:
        best.resolve(agendas_[0])
    value(
        "play-informed",
        "outcome of the player who reads the conditions and proposes a passing agenda each time (1 = won in three)",
        best.outcome is Outcome.WON and len(best.history) == 3,
        1,
    )

    # S07: resolve
    session = CouncilSession("s")
    session.resolve(Agenda(False, False, False))
    value(
        "attempt-cost",
        "attempts left after one rejected agenda (theory 1)",
        session.attempts_left,
        1,
    )
    session.resolve(passing[0][0])
    value(
        "attempt-restored",
        "attempts left after an approval moves to the next council (theory 2)",
        session.attempts_left,
        2,
    )
    lost = CouncilSession("l")
    lost.resolve(Agenda(False, False, False))
    events = lost.resolve(Agenda(False, False, False))
    value(
        "events-on-loss",
        "events returned by the losing resolution (theory 2: AgendaResolved, SessionEnded)",
        len(events),
        2,
    )
    try:
        lost.resolve(passing[0][0])
        kept = 0
    except SessionFinished:
        kept = 1
    value("finished-refuses", "a finished session raises SessionFinished (theory 1)", kept, 1)
    value(
        "finished-history",
        "resolutions recorded after that refusal (theory 2: nothing was added)",
        len(lost.history),
        2,
    )
    fresh = CouncilSession("f")
    try:
        fresh.resolve("lamps")  # type: ignore[arg-type]
    except TypeError:
        pass
    value(
        "invalid-free",
        "attempts left after a proposal that is not an Agenda (theory 2: none consumed)",
        fresh.attempts_left,
        2,
    )

    lines = [
        "# Measured values",
        "",
        "Written by `make theory-figs` (scripts/theory_figs.py) from the domain itself. Do not edit by hand.",
        "The last column is the relative error; where the theory column is 0 it is the absolute value.",
        "",
        "| id | what is measured | measured | theory | error |",
        "|---|---|---|---|---|",
        *ROWS,
    ]
    (OUT / "values.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
