# Council Vote

A single-player logic game about assembling agendas that satisfy a council's
public voting conditions. M2 implements the rules as a pure domain: agendas of
three clauses, five seats with public conditions, quorum and strict majority,
three fixed councils and a session of two attempts per council. M3 adds
framework-independent start/resolve/read use cases and SQLite persistence.
Browser play is planned for M4; there is no playable screen yet.

The rules can be tried from Python without Django:

```sh
PYTHONPATH=src python3 -c "
from council_vote.domain import Agenda, CouncilSession
session = CouncilSession('demo')
for event in session.resolve(Agenda(lamps=True, gate=True, bell=False)):
    print(event)
"
```

**Theory handbook**: [docs/theory/](docs/theory/README.md) — 9 statements (the language, the agenda
value, a seat's condition, quorum and majority, the three councils as boards, the session, one proposal
step by step, determinism and the chance of guessing, the dependency rule), each with its rule,
assumptions, derivation, code, tests and a figure. `make theory-figs` regenerates the figures and the
measured values; `make theory-check` checks the coverage table.

Requires Python 3.14 and [uv](https://docs.astral.sh/uv/).

```sh
make sync
make check
make serve
```

`make serve` applies migrations and starts the local server. Its SQLite database
is `test-results/council-vote.sqlite3` (ignored by Git); set
`COUNCIL_VOTE_DB_PATH` to use another file. Open
`http://localhost:8000/health/` for `{"status":"ok"}`. The development entry
generates an ephemeral signing key in memory; no credential is stored. This
scaffold is for local use and is not deployment configuration.

`make test` runs unit tests. `make check` also runs SQLite integration tests,
Ruff, mypy, Import Linter and Django system checks. Both save native JUnit and
`test-results/summary.json` outside Git.
Benchmarks and browser smoke checks begin when gameplay exists. CI runs only
lightweight pull request checks; no push or scheduled test execution.

See the [domain vocabulary and roadmap](docs/domain.md),
[requirements](docs/requirements.md) and [test inventory](test-inventory.json).
[M2](https://github.com/TM-59/council-vote/issues/2) added the pure domain,
[M3](https://github.com/TM-59/council-vote/issues/3) added use cases and Django
ORM/SQLite migrations, and [M4](https://github.com/TM-59/council-vote/issues/4)
adds one browser screen. No external images, sounds or fonts are needed.
