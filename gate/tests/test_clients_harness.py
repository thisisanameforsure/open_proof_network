"""F16-T7 / AC9 (marker ``harness``): each connector against its real harness binary.

Run by ``make verify-harness`` with the binaries from ``gate/clients/harness/package-lock.json``
on the path or in ``OPN_HARNESS_BIN``. Each entry and token form is checked by
``gate/tools/harness_check.py``: a ``fail`` fails here with the harness's own output; a check the
environment cannot attempt (no binary, no credential) is skipped with the runner's reason, and the
runner's report, which is the task's evidence, counts it against the verdict (F16-R10).
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from test_harness_check import runner

from opn_gate import clients

pytestmark = pytest.mark.harness
REGISTRY = clients.load()
BIN = Path(os.environ["OPN_HARNESS_BIN"]).resolve() if os.environ.get("OPN_HARNESS_BIN") else None


@pytest.fixture(scope="module")
def served() -> Iterator[Any]:
    s = runner.serve()
    yield s
    s.stop()


@pytest.mark.parametrize("auth", ["none", "bearer"])
@pytest.mark.parametrize("entry_id", [e.id for e in REGISTRY.entries])
def test_list_check(served: Any, entry_id: str, auth: str) -> None:
    result = runner.check(served, REGISTRY, REGISTRY.by_id(entry_id), auth=auth, bin_dir=BIN)
    if result.state == runner.NOT_ATTEMPTED:
        pytest.skip(f"not attempted: {result.reason}")
    assert result.state == runner.PASS, f"{result.reason}\n{result.output_tail}"


@pytest.mark.parametrize("entry_id", [e.id for e in REGISTRY.entries])
def test_broken_snippet_fails(served: Any, entry_id: str) -> None:
    """AC9: the same check against a registry whose snippet points at a path the server does not
    serve fails, with the harness's own output kept, so a pass above means something."""
    import yaml  # noqa: PLC0415

    doc = yaml.safe_load(clients.REGISTRY_PATH.read_text(encoding="utf-8"))
    for entry in doc["entries"]:
        for snippet in entry["snippets"]:
            snippet["template"] = snippet["template"].replace("{{mcp_url}}", "{{mcp_url}}-nowhere")
    broken = clients.parse(doc)
    result = runner.check(served, broken, broken.by_id(entry_id), bin_dir=BIN)
    if result.state == runner.NOT_ATTEMPTED:
        pytest.skip(f"not attempted: {result.reason}")
    assert result.state == runner.FAIL, result
