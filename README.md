# Council Vote

A single-player logic game about assembling agendas that satisfy a council's
public voting conditions. The current M1 establishes vocabulary, dependency
boundaries and a Django health route. Voting rules, persistence and browser
play are planned for M2 through M4. There is no playable screen yet.

Requires Python 3.14 and [uv](https://docs.astral.sh/uv/).

```sh
make sync
make check
make serve
```

Open `http://localhost:8000/health/` for `{"status":"ok"}`. The development
entry generates an ephemeral signing key in memory; no credential is stored.
This scaffold is for local use and is not deployment configuration.

`make test` runs pytest. `make check` adds Ruff, mypy, Import Linter and Django
system checks. Both save native JUnit and `test-results/summary.json` outside Git.
Benchmarks and browser smoke checks begin when gameplay exists. CI runs only
lightweight pull request checks; no push or scheduled test execution.

See the [domain vocabulary and roadmap](docs/domain.md),
[requirements](docs/requirements.md) and [test inventory](test-inventory.json).
[M2](https://github.com/TM-59/council-vote/issues/2) adds the pure domain,
[M3](https://github.com/TM-59/council-vote/issues/3) adds use cases and Django
ORM/SQLite migrations, and [M4](https://github.com/TM-59/council-vote/issues/4)
adds one browser screen. No external images, sounds or fonts are needed.
