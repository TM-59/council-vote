import subprocess
import sys

from django.test import Client


def test_REQ_HEALTH_get_returns_json(client: Client) -> None:
    response = client.get("/health/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_REQ_HEALTH_rejects_post(client: Client) -> None:
    assert client.post("/health/").status_code == 405


def test_REQ_CORE_imports_without_frameworks() -> None:
    subprocess.run(
        [sys.executable, "-S", "-c", "import council_vote.domain, council_vote.application"],
        env={"PYTHONPATH": "src"},
        timeout=10,
        check=True,
    )


def test_REQ_HEALTH_unknown_route_is_not_implemented(client: Client) -> None:
    assert client.get("/").status_code == 404
