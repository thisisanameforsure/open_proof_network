"""F13-T5 / AC9: the target page names the hosted checker that serves its Mathlib pin, read from
the network's mapping (``opn_gate.hosted``) and never from the graph (F13-R11, Q9, Q12)."""

from __future__ import annotations

import json
from pathlib import Path

import fixture
import pytest

from opn_gate import hosted
from opn_site import model, render

REPO = "https://github.com/example/graph"
PIN = "0df444a360eaa60ab8c11dca51a86af692955474"  # gate/mathlib-pins.txt, v4.33.1
PAGE = "targets/propositional/index.html"
LEAD = "Fast check (POST /check, non-authoritative): "


def page_for(root: Path, sha: str | None) -> str:
    index = root / "targets" / "index.json"
    doc = json.loads(index.read_text(encoding="utf-8"))
    for entry in doc["targets"]:
        if entry["target_id"] == "propositional":
            entry["mathlib_sha"] = sha
    index.write_text(json.dumps(doc), encoding="utf-8")
    return render.render_site(model.load_site(root, fixture.COMMIT), repo_url=REPO)[PAGE]


def test_target_page_names_fast_check(tmp_path_factory: pytest.TempPathFactory) -> None:
    """A Lean-core-only target names the core environment (Q9); a pin the mapping serves names
    its environment and how near it is; a pin the mapping lacks says none."""
    mapping = hosted.load()
    assert mapping.core is not None

    core = page_for(fixture.build(tmp_path_factory.mktemp("core")), None)
    assert f"{LEAD}{mapping.core.environment} on AXLE (nearest: a Lean-core-only statement" in core

    pinned = page_for(fixture.build(tmp_path_factory.mktemp("pinned")), PIN)
    assert f"{LEAD}{mapping.pins[PIN].environment} on AXLE (exact)" in pinned

    unmapped = page_for(fixture.build(tmp_path_factory.mktemp("unmapped")), "1" * 40)
    assert f"{LEAD}none: no hosted environment serves this Mathlib pin" in unmapped


def test_a_core_target_without_a_core_entry_says_none(
    tmp_path_factory: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Q9: the core entry is optional, and its absence is said, not guessed."""
    monkeypatch.setattr(hosted, "load", lambda path=None: hosted.HostedMapping())
    html = page_for(fixture.build(tmp_path_factory.mktemp("no-core")), None)
    assert f"{LEAD}none: no hosted environment serves a Lean-core-only target" in html


def test_an_unreadable_mapping_is_said_not_hidden(
    tmp_path_factory: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    """C7: a site build without the mapping still renders, and says it could not read it."""

    def broken(path: Path = hosted.MAPPING_PATH) -> hosted.HostedMapping:
        msg = "hosted-checkers.yaml is not hosted-checkers/v1"
        raise hosted.MappingError(msg)

    monkeypatch.setattr(hosted, "load", broken)
    html = page_for(fixture.build(tmp_path_factory.mktemp("broken")), PIN)
    assert "unknown: the hosted-checker mapping could not be read" in html
