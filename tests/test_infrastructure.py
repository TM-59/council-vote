# Copyright 2026 TM-59
"""The Django repository against SQLite: persistence across processes and atomic saves."""

import json
import os
import secrets
import subprocess
import sys
from pathlib import Path
from typing import cast

import pytest
from django.db import connection

from council_vote.composition.session import build_session_use_cases
from council_vote.domain import Agenda, CouncilSession, NotAnAgendaError, SessionFinishedError
from council_vote.infrastructure.repository import DjangoSessionRepository

WINNING = (
    Agenda(lamps=True, gate=True, bell=False),
    Agenda(lamps=False, gate=False, bell=True),
    Agenda(lamps=False, gate=True, bell=True),
)
REJECTED = Agenda(lamps=False, gate=False, bell=False)


@pytest.mark.integration
@pytest.mark.django_db(transaction=True)
def test_req_persistence_session_and_history_survive_a_process_restart() -> None:
    """REQ-PERSISTENCE: another process reads the stored session and history."""
    use_cases = build_session_use_cases()
    session = use_cases.start.execute()
    use_cases.resolve.execute(session.session_id, WINNING[0])

    env = os.environ.copy()
    env.update(
        COUNCIL_VOTE_DB_PATH=str(Path(str(connection.settings_dict["NAME"])).resolve()),
        COUNCIL_VOTE_SECRET_KEY=secrets.token_urlsafe(48),
        COUNCIL_VOTE_SESSION_ID=session.session_id,
        DJANGO_SETTINGS_MODULE="council_vote.composition.settings",
        PYTHONPATH="src",
    )
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import json, os\n"
                "import django\n"
                "django.setup()\n"
                "from council_vote.composition.session import build_session_use_cases\n"
                "use_cases = build_session_use_cases()\n"
                "session = use_cases.read.execute(os.environ['COUNCIL_VOTE_SESSION_ID'])\n"
                "print(json.dumps({'council': session.council, 'attempts_left': "
                "session.attempts_left, 'history': len(session.history), "
                "'agenda': session.history[0].agenda.lamps}))\n"
            ),
        ],
        capture_output=True,
        check=False,
        text=True,
        timeout=10,
        env=env,
    )

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {
        "council": 1,
        "attempts_left": 2,
        "history": 1,
        "agenda": True,
    }


@pytest.mark.integration
@pytest.mark.django_db(transaction=True)
def test_req_atomic_invalid_and_finished_resolutions_do_not_write() -> None:
    """REQ-ATOMIC: refused resolutions leave the stored record unchanged."""
    repository = DjangoSessionRepository()
    use_cases = build_session_use_cases()
    session = use_cases.start.execute()
    resolve = use_cases.resolve

    before_invalid = repository.get(session.session_id)
    assert before_invalid is not None
    with pytest.raises(NotAnAgendaError):
        resolve.execute(session.session_id, cast("Agenda", None))
    assert repository.get(session.session_id) == before_invalid

    for agenda in WINNING:
        resolve.execute(session.session_id, agenda)
    before_finished = repository.get(session.session_id)
    assert before_finished is not None
    with pytest.raises(SessionFinishedError):
        resolve.execute(session.session_id, REJECTED)
    assert repository.get(session.session_id) == before_finished


@pytest.mark.integration
@pytest.mark.django_db(transaction=True)
def test_req_atomic_stale_competing_update_is_rejected_without_overwrite() -> None:
    """REQ-ATOMIC: a stale save is refused and the first save is kept."""
    repository = DjangoSessionRepository()
    repository.add(CouncilSession("competing-session"))
    first = repository.get("competing-session")
    stale = repository.get("competing-session")
    assert first is not None
    assert stale is not None

    first.session.resolve(WINNING[0])
    assert repository.save(first)
    stale.session.resolve(REJECTED)
    assert not repository.save(stale)

    committed = repository.get("competing-session")
    assert committed is not None
    assert committed.version == 1
    assert committed.session.history == first.session.history
    assert committed.session.council == 1
