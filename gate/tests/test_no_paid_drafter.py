"""F21-AC1 (R1, Q9): the network drafts nothing at its own expense.

The drafting modules, the workflow the graph's outline job dispatches, the ``gloss draft``
command, the ``OPN_DRAFTER_*`` settings and the service's ``drafter`` request field are gone. What
stays, on the owner's word (Q9), lies outside the code: the secrets, the saved token, the stack
parameter and the graph's dispatch step, which finds no ``gloss-draft.yml`` to start. The readers
of the seven existing drafter blocks stay too (schemas, products, the site), which is why this
guard names files and fields rather than the word.
"""

from __future__ import annotations

import argparse
import dataclasses
from pathlib import Path

from opn_api import glosses as api_glosses
from opn_gate import cli, config

REPO = Path(__file__).resolve().parents[2]


def _subcommands(parser: argparse.ArgumentParser) -> dict[str, argparse.ArgumentParser]:
    for action in parser._actions:  # argparse exposes no public walk of its subparsers
        if isinstance(action, argparse._SubParsersAction):
            return dict(action.choices)
    return {}


def test_no_drafting_module_or_workflow() -> None:
    present = [
        rel
        for rel in (
            "gate/opn_gate/drafter.py",
            "gate/opn_gate/draft_run.py",
            ".github/workflows/gloss-draft.yml",
        )
        if (REPO / rel).exists()
    ]
    assert present == [], f"the paid drafter is still in the tree: {present}"


def test_no_gloss_draft_command() -> None:
    gloss = _subcommands(cli.build_parser())["gloss"]
    assert "draft" not in _subcommands(gloss), "`opn-gate gloss draft` still exists"


def test_no_drafter_setting() -> None:
    fields = [f.name for f in dataclasses.fields(config.Settings) if f.name.startswith("drafter")]
    assert fields == [], f"the gate still reads OPN_DRAFTER_* settings: {fields}"
    source = (REPO / "gate/opn_gate/config.py").read_text(encoding="utf-8")
    assert "OPN_DRAFTER_" not in source


def test_the_service_takes_no_drafter_field() -> None:
    assert "drafter" not in api_glosses.GLOSS_FIELDS
    assert not hasattr(api_glosses, "drafter_of")
    assert not hasattr(api_glosses, "DRAFTER_KEYS")
