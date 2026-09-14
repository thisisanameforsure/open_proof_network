"""F13-T1: every Mathlib pin names its release tag (R1) and has exactly one hosted-checker entry
(R2), so a new pin cannot land without saying which fast checker serves it, or that none does."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
PINS = ROOT / "gate" / "mathlib-pins.txt"
CHECKERS = ROOT / "gate" / "hosted-checkers.yaml"

SHA = re.compile(r"[0-9a-f]{40}")
TAG = re.compile(r"v\d+\.\d+\.\d+")
ENVIRONMENT = re.compile(r"lean-\d+\.\d+\.\d+")


def pin_lines(text: str) -> list[tuple[str, str]]:
    """Each pin line as (sha, tag comment); comment-only and blank lines are skipped."""
    pins = []
    for line in text.splitlines():
        code, _, comment = line.partition("#")
        if code.strip():
            pins.append((code.strip(), comment.strip()))
    return pins


def coverage_problems(pins_text: str, doc: dict[str, Any]) -> list[str]:
    """What is wrong with the pins file and the mapping together; empty when they agree."""
    problems = []
    if doc.get("schema") != "hosted-checkers/v1":
        problems.append(f"schema is {doc.get('schema')!r}, not 'hosted-checkers/v1'")
    if doc.get("service") != "axle":
        problems.append(f"service is {doc.get('service')!r}, not 'axle'")
    entries = doc.get("pins") or {}
    listed = pin_lines(pins_text)
    for sha, tag in listed:
        if not SHA.fullmatch(sha):
            problems.append(f"{sha!r} is not a 40-hex commit")
            continue
        if not TAG.fullmatch(tag):
            problems.append(f"{sha} names no release tag (got {tag!r})")
        entry = entries.get(sha)
        if entry is None:
            problems.append(f"{sha} has no entry in hosted-checkers.yaml")
            continue
        if entry.get("mathlib_tag") != tag:
            problems.append(f"{sha}: mapping says {entry.get('mathlib_tag')!r}, pins say {tag!r}")
        env = entry.get("environment")
        if env is not None and not (isinstance(env, str) and ENVIRONMENT.fullmatch(env)):
            problems.append(f"{sha}: environment {env!r} is not lean-X.Y.Z or null")
        if not isinstance(entry.get("exact"), bool):
            problems.append(f"{sha}: exact must be true or false")
        if env is not None and entry.get("exact") is False and not entry.get("note"):
            problems.append(f"{sha}: a nearest environment needs a note saying what differs")
    for sha in set(entries) - {sha for sha, _ in listed}:
        problems.append(f"{sha} is in hosted-checkers.yaml but not pinned")
    return problems


def test_every_pin_has_a_tag_and_one_checker_entry() -> None:
    """R1, R2: the committed files agree."""
    doc = yaml.safe_load(CHECKERS.read_text(encoding="utf-8"))
    assert coverage_problems(PINS.read_text(encoding="utf-8"), doc) == []


GOOD: dict[str, Any] = {
    "schema": "hosted-checkers/v1",
    "service": "axle",
    "pins": {
        "a" * 40: {
            "mathlib_tag": "v4.33.1",
            "environment": "lean-4.33.0",
            "exact": False,
            "note": "toolchain bump",
        }
    },
}


@pytest.mark.parametrize(
    ("pins_text", "pins", "problem"),
    [
        (f"{'a' * 40}\n", GOOD["pins"], "names no release tag"),
        (f"{'b' * 40}  # v4.34.0\n", GOOD["pins"], "has no entry"),
        (
            f"{'a' * 40}  # v4.33.1\n",
            {"a" * 40: {**GOOD["pins"]["a" * 40], "mathlib_tag": "v4.33.0"}},
            "pins say",
        ),
        (
            f"{'a' * 40}  # v4.33.1\n",
            {"a" * 40: {**GOOD["pins"]["a" * 40], "note": None}},
            "needs a note",
        ),
        (
            f"{'a' * 40}  # v4.33.1\n",
            {"a" * 40: {**GOOD["pins"]["a" * 40], "environment": "4.33"}},
            "not lean-X.Y.Z",
        ),
        (
            f"{'a' * 40}  # v4.33.1\n",
            {"a" * 40: {**GOOD["pins"]["a" * 40], "exact": "no"}},
            "exact must be",
        ),
        (
            f"{'a' * 40}  # v4.33.1\n",
            {**GOOD["pins"], "c" * 40: GOOD["pins"]["a" * 40]},
            "but not pinned",
        ),
    ],
)
def test_each_disagreement_is_named(pins_text: str, pins: dict[str, Any], problem: str) -> None:
    """R1, R2: a missing tag, a missing or stale entry, a malformed environment, an unexplained
    nearest match and an orphan entry are each refused by name."""
    problems = coverage_problems(pins_text, {**GOOD, "pins": pins})
    assert any(problem in p for p in problems), problems


def test_no_environment_is_allowed_but_must_be_said() -> None:
    """R2: a pin AXLE does not host is an explicit null, not a missing entry."""
    pins = {"a" * 40: {"mathlib_tag": "v4.33.1", "environment": None, "exact": False}}
    assert coverage_problems(f"{'a' * 40}  # v4.33.1\n", {**GOOD, "pins": pins}) == []


def test_the_workflows_still_read_the_tagged_line() -> None:
    """R1: the publish and CI workflows strip comments with sed before matching 40 hex, so a
    trailing tag comment leaves the matrix unchanged."""
    import subprocess  # noqa: PLC0415

    out = subprocess.run(
        [
            "sh",
            "-c",
            "sed -e 's/#.*//' -e 's/[[:space:]]//g' \"$1\" | grep -E '^[0-9a-f]{40}$'",
            "sh",
            str(PINS),
        ],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()
    assert out == [sha for sha, _ in pin_lines(PINS.read_text(encoding="utf-8"))]
