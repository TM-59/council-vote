"""Bounded local checks; keep native JUnit and record failures as well as passes."""

import json
import os
import platform
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path

started = datetime.now(UTC)
clock = time.monotonic()
run_id = started.strftime("%Y%m%dT%H%M%S%fZ")
folder = Path("test-results") / run_id
folder.mkdir(parents=True)
junit = folder / "unit-pytest.xml"
mode = sys.argv[1]
if mode not in {"test", "check"}:
    raise SystemExit("expected test or check")
commands = [
    [
        sys.executable,
        "-m",
        "pytest",
        "-q",
        "-m",
        "not integration",
        f"--junitxml={junit}",
    ]
]
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
    integration_junit = folder / "integration-pytest.xml"
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
    commands += [
        ["ruff", "check", "."],
        ["ruff", "format", "--check", "."],
        ["mypy"],
        ["lint-imports", "--no-cache"],
        [sys.executable, "manage.py", "check"],
        [sys.executable, "manage.py", "makemigrations", "--check", "--dry-run"],
    ]
results = []
durations = []
for command in commands:
    while os.getloadavg()[0] > 20:
        time.sleep(5)
    command_started = time.monotonic()
    try:
        result = subprocess.run(command, timeout=60, check=False)
        results.append(result.returncode)
    except subprocess.TimeoutExpired, OSError:
        results.append(124)
    durations.append(round(time.monotonic() - command_started, 3))
suite_counts = []
for _kind, _command, report, _requirements in test_suites:
    counts = dict(tests=0, failures=0, errors=0, skipped=0)
    if report.exists():
        for case in ET.parse(report).iter("testcase"):
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
git = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True)
dirty = subprocess.run(
    ["git", "status", "--porcelain"], capture_output=True, text=True, check=True
).stdout
summary = dict(
    schema_version=1,
    run_id=run_id,
    repository="TM-59/council-vote",
    commit=git.stdout.strip(),
    dirty=bool(dirty),
    started_at=started.isoformat(),
    finished_at=datetime.now(UTC).isoformat(),
    duration_seconds=round(time.monotonic() - clock, 3),
    status=status,
    exit_code=0 if status == "pass" else 1,
    environment=dict(
        os=platform.system(),
        architecture=platform.machine(),
        tools={"python": platform.python_version()},
        jobs=1,
        seed=None,
    ),
    counts=counts,
    coverage=dict(
        status="not_measured",
        line_percent=None,
        branch_percent=None,
        reason="Coverage is not measured by this local runner.",
    ),
    metrics=[
        dict(
            name=f"check_{index}_exit",
            status="pass" if code == 0 else "fail",
            value=code,
            unit="exit_code",
            threshold=0,
            comparison="eq",
            reason="check timed out or failed to start" if code == 124 else None,
        )
        for index, code in enumerate(results[len(test_suites) :])
    ],
    suites=[
        dict(
            kind=kind,
            framework="pytest",
            command=command,
            status="pass" if results[index] == 0 and suite_counts[index]["tests"] else "fail",
            duration_seconds=durations[index],
            counts=suite_counts[index],
            junit=str(report) if report.exists() else None,
            requirements=requirements,
            reason="test process timed out or failed to start" if results[index] == 124 else None,
        )
        for index, (kind, command, report, requirements) in enumerate(test_suites)
    ],
)
text = json.dumps(summary, indent=2) + "\n"
(folder / "summary.json").write_text(text)
Path("test-results/summary.json").write_text(text)
raise SystemExit(summary["exit_code"])
