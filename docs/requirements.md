# Requirements (M1–M3)

- REQ-HEALTH: GET /health/ returns status ok as JSON; other methods are rejected.
- REQ-CORE: domain/application import without frameworks; adapters point inward.
- REQ-CHECK: local make checks save native JUnit and a summary, including failures.

Test names carry requirement IDs. Import Linter also enforces REQ-CORE.
REQ-CHECK is verified with isolated failure/timeout runs during scaffold acceptance.

M2, the pure domain (standard library only):

- REQ-VOTE: an agenda is approved only with at least three non-abstaining ballots and more yes than no; a tie is rejected.
- REQ-AGENDA: an agenda is an immutable value of three true/false clauses; eight exist.
- REQ-SEAT: a seat's public condition yields exactly one ballot; abstaining is checked first.
- REQ-COUNCIL: a council has five distinct seats; the three fixed councils have 3, 2 and 2 passing agendas, found by enumeration.
- REQ-SESSION: two attempts per council; approval advances and restores attempts; three approvals win; running out loses; finished sessions and invalid agendas change nothing.

M3, application and persistence:

- REQ-USECASE: start a session, resolve an agenda through the domain, and read a session without coupling the application to Django.
- REQ-PERSISTENCE: SQLite stores the session state and complete resolution history; a fresh process can restore them.
- REQ-ATOMIC: invalid agendas and finished sessions do not write; a concurrent stale update is rejected without overwriting the committed state.
