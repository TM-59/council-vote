import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from django.db import connection

from council_vote.composition.session import build_session_use_cases
from council_vote.domain import Agenda, CouncilSession, SessionFinished
from council_vote.infrastructure.repository import DjangoSessionRepository

WINNING = (Agenda(True, True, False), Agenda(False, False, True), Agenda(False, True, True))
REJECTED = Agenda(False, False, False)


@pytest.mark.integration
@pytest.mark.django_db(transaction=True)
def test_REQ_PERSISTENCE_session_and_history_survive_a_process_restart() -> None:
    use_cases = build_session_use_cases()
    session = use_cases.start.execute()
    use_cases.resolve.execute(session.session_id, WINNING[0])

    child = (
        "import json, os, sys\n"
        "os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'council_vote.composition.settings')\n"
        "import django\n"
        "django.setup()\n"
        "from council_vote.composition.session import build_session_use_cases\n"
        "session = build_session_use_cases().read.execute(sys.argv[1])\n"
        "print(json.dumps({'council': session.council, 'attempts_left': "
        "session.attempts_left, 'history': len(session.history), "
        "'agenda': session.history[0].agenda.lamps}))\n"
    )
    env = os.environ.copy()
    env.update(
        COUNCIL_VOTE_DB_PATH=str(Path(str(connection.settings_dict["NAME"])).resolve()),
        COUNCIL_VOTE_SECRET_KEY="integration-test-key",
        PYTHONPATH="src",
    )
    result = subprocess.run(
        [sys.executable, "-c", child, session.session_id],
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
def test_REQ_ATOMIC_invalid_and_finished_resolutions_do_not_write() -> None:
    repository = DjangoSessionRepository()
    use_cases = build_session_use_cases()
    session = use_cases.start.execute()
    resolve = use_cases.resolve

    before_invalid = repository.get(session.session_id)
    assert before_invalid is not None
    with pytest.raises(TypeError):
        resolve.execute(session.session_id, None)  # type: ignore[arg-type]
    assert repository.get(session.session_id) == before_invalid

    for agenda in WINNING:
        resolve.execute(session.session_id, agenda)
    before_finished = repository.get(session.session_id)
    assert before_finished is not None
    with pytest.raises(SessionFinished):
        resolve.execute(session.session_id, REJECTED)
    assert repository.get(session.session_id) == before_finished


@pytest.mark.integration
@pytest.mark.django_db(transaction=True)
def test_REQ_ATOMIC_stale_competing_update_is_rejected_without_overwrite() -> None:
    repository = DjangoSessionRepository()
    repository.add(CouncilSession("competing-session"))
    first = repository.get("competing-session")
    stale = repository.get("competing-session")
    assert first is not None and stale is not None

    first.session.resolve(WINNING[0])
    assert repository.save(first)
    stale.session.resolve(REJECTED)
    assert not repository.save(stale)

    committed = repository.get("competing-session")
    assert committed is not None
    assert committed.version == 1
    assert committed.session.history == first.session.history
    assert committed.session.council == 1
