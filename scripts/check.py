# Copyright 2026 TM-59
"""Bounded local checks; keep native JUnit and record failures as well as passes."""

import json
import os
import platform
import subprocess
import sys
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from defusedxml import ElementTree

LOAD_LIMIT = 20  # wait while the machine's one-minute load average is above this
TIMED_OUT = 124  # exit code recorded when a step times out or cannot start
STEP_SECONDS = 60

started = datetime.now(UTC)
clock = time.monotonic()
run_id = started.strftime("%Y%m%dT%H%M%S%fZ")
folder = Path("test-results") / run_id
folder.mkdir(parents=True)
junit = folder / "unit-pytest.xml"
integration_junit = folder / "integration-pytest.xml"
mode = sys.argv[1]
if mode not in {"test", "check"}:
    message = "expected test or check"
    raise SystemExit(message)


def _junit_env(report: Path) -> dict[str, str]:
    """Return the environment that makes pytest write its JUnit report to `report`."""
    return {**os.environ, "PYTEST_ADDOPTS": f"--junitxml={report}"}


# Each step is spelled out as a literal command so that what runs is visible in one place.
Step = Callable[[], subprocess.CompletedProcess[bytes]]
steps: list[Step] = [
    lambda: subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-m", "not integration"],
        env=_junit_env(junit),
        timeout=STEP_SECONDS,
        check=False,
    )
]
commands = [[sys.executable, "-m", "pytest", "-q", "-m", "not integration", f"--junitxml={junit}"]]
test_suites = [
    (
        "unit",
        commands[0],
        junit,
        [
            "REQ-HEALTH",
            "REQ-CORE",
            "REQ-CHECK",
            "REQ-VOTE",
            "REQ-AGENDA",
            "REQ-SEAT",
            "REQ-COUNCIL",
            "REQ-SESSION",
            "REQ-USECASE",
        ],
    )
]
if mode == "check":
    integration_command = [
        sys.executable,
        "-m",
        "pytest",
        "-q",
        "-m",
        "integration",
        f"--junitxml={integration_junit}",
    ]
    commands.append(integration_command)
    test_suites.append(
        (
            "integration",
            integration_command,
            integration_junit,
            ["REQ-PERSISTENCE", "REQ-ATOMIC"],
        )
    )
    steps += [
        lambda: subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "-m", "integration"],
            env=_junit_env(integration_junit),
            timeout=STEP_SECONDS,
            check=False,
        ),
        lambda: subprocess.run(
            [sys.executable, "-m", "ruff", "check", "."], timeout=STEP_SECONDS, check=False
        ),
        lambda: subprocess.run(
            [sys.executable, "-m", "ruff", "format", "--check", "."],
            timeout=STEP_SECONDS,
            check=False,
        ),
        lambda: subprocess.run([sys.executable, "-m", "mypy"], timeout=STEP_SECONDS, check=False),
        lambda: subprocess.run(
            [
                sys.executable,
                "-c",
                (
                    "import sys; from importlinter.cli import lint_imports_command; "
                    "sys.exit(lint_imports_command())"
                ),
                "--no-cache",
            ],
            timeout=STEP_SECONDS,
            check=False,
        ),
        lambda: subprocess.run(
            [sys.executable, "manage.py", "check"], timeout=STEP_SECONDS, check=False
        ),
        lambda: subprocess.run(
            [sys.executable, "manage.py", "makemigrations", "--check", "--dry-run"],
            timeout=STEP_SECONDS,
            check=False,
        ),
    ]
results = []
durations = []
for step in steps:
    while os.getloadavg()[0] > LOAD_LIMIT:
        time.sleep(5)
    command_started = time.monotonic()
    try:
        results.append(step().returncode)
    except subprocess.TimeoutExpired, OSError:
        results.append(TIMED_OUT)
    durations.append(round(time.monotonic() - command_started, 3))
suite_counts = []
for _kind, _command, report, _requirements in test_suites:
    counts = {"tests": 0, "failures": 0, "errors": 0, "skipped": 0}
    if report.exists():
        for case in ElementTree.parse(report).iter("testcase"):
            counts["tests"] += 1
            for node, key in [
                ("failure", "failures"),
                ("error", "errors"),
                ("skipped", "skipped"),
            ]:
                counts[key] += int(case.find(node) is not None)
    suite_counts.append(counts)
counts = {
    key: sum(suite[key] for suite in suite_counts)
    for key in ("tests", "failures", "errors", "skipped")
}
tests_pass = all(
    results[index] == 0 and suite_counts[index]["tests"] for index in range(len(test_suites))
)
checks_pass = not any(results[len(test_suites) :])
status = "pass" if tests_pass and checks_pass else "fail"
git = subprocess.run(
    ["/usr/bin/git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True
)
dirty = subprocess.run(
    ["/usr/bin/git", "status", "--porcelain"], capture_output=True, text=True, check=True
).stdout
summary = {
    "schema_version": 1,
    "run_id": run_id,
    "repository": "TM-59/council-vote",
    "commit": git.stdout.strip(),
    "dirty": bool(dirty),
    "started_at": started.isoformat(),
    "finished_at": datetime.now(UTC).isoformat(),
    "duration_seconds": round(time.monotonic() - clock, 3),
    "status": status,
    "exit_code": 0 if status == "pass" else 1,
    "environment": {
        "os": platform.system(),
        "architecture": platform.machine(),
        "tools": {"python": platform.python_version()},
        "jobs": 1,
        "seed": None,
    },
    "counts": counts,
    "coverage": {
        "status": "not_measured",
        "line_percent": None,
        "branch_percent": None,
        "reason": "Coverage is not measured by this local runner.",
    },
    "metrics": [
        {
            "name": f"check_{index}_exit",
            "status": "pass" if code == 0 else "fail",
            "value": code,
            "unit": "exit_code",
            "threshold": 0,
            "comparison": "eq",
            "reason": "check timed out or failed to start" if code == TIMED_OUT else None,
        }
        for index, code in enumerate(results[len(test_suites) :])
    ],
    "suites": [
        {
            "kind": kind,
            "framework": "pytest",
            "command": command,
            "status": "pass" if results[index] == 0 and suite_counts[index]["tests"] else "fail",
            "duration_seconds": durations[index],
            "counts": suite_counts[index],
            "junit": str(report) if report.exists() else None,
            "requirements": requirements,
            "reason": "test process timed out or failed to start"
            if results[index] == TIMED_OUT
            else None,
        }
        for index, (kind, command, report, requirements) in enumerate(test_suites)
    ],
}
text = json.dumps(summary, indent=2) + "\n"
(folder / "summary.json").write_text(text)
Path("test-results/summary.json").write_text(text)
raise SystemExit(summary["exit_code"])
