"""F19 fixtures: outlines written by hand in the ``outline/v1`` shape (T2's committed contract).

The Lean extractor is built elsewhere (F19-T1, T3), so these documents are what it would write for
the proofs below, kept small enough to check by eye against the Lean: every span names the lines
it says, every claim is the step's type as written. Each is validated against the schema before a
test uses it, so a fixture that drifts from the contract fails here rather than on the page.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from harness import TARGET

from opn_gate import schemas

OUTLINE_SCHEMA = "outline/v1"
GATE = "7" * 40

#: The tutorial node's proof, rewritten so its outline has every shape AC10 names: a nested step
#: (``hq`` holds an ``obtain``), a step closed by automation (``hp``, ``simp``) and a step whose
#: printed claim did not read back (the ``show``).
TUTORIAL_PROOF = """\
/-! The tutorial node (D-27): permanently open, off-ledger. Lean core only. -/

theorem OpnProp.and_swap : ∀ p q : Prop, p ∧ q → q ∧ p := by
  intro p q h
  have hq : q := by
    obtain ⟨_, hq⟩ := h
    exact hq
  have hp : p := by simp [h.1]
  show q ∧ p
  exact ⟨hq, hp⟩
"""
#: What the stubbed printer wrote for the ``show`` step: not the Lean's claim, so the page must
#: not show it (F19-R3: an unreliable step is its Lean lines only).
UNRELIABLE_TEXT = "↑q ∧ ↑p -- misprinted"
AND_LEFT_DOC = "Extract the left conjunct from a conjunction, <b>escaped</b>."
STACKS_TAG = "0ABC"


def text(value: str, *, printed: str = "reliable") -> dict[str, Any]:
    return {"text": value, "printed": printed, "truncated": False}


def step(
    step_id: str,
    kind: str,
    lines: tuple[int, int],
    *,
    name: str | None = None,
    claim: dict[str, Any] | None = None,
    goal: dict[str, Any] | None = None,
    closed_by: tuple[str, list[str]] = ("steps", []),
    nodes: list[str] | None = None,
    mathlib: list[dict[str, Any]] | None = None,
    child_node: str | None = None,
    children: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "id": step_id,
        "kind": kind,
        "name": name,
        "claim": claim,
        "goal": goal,
        "span": {"start_line": lines[0], "end_line": lines[1]},
        "uses": {"nodes": nodes or [], "defs": [], "mathlib": mathlib or []},
        "closed_by": {"kind": closed_by[0], "tactics": closed_by[1]},
        "child_node": child_node,
        "children": children or [],
    }


def tutorial_steps() -> list[dict[str, Any]]:
    return [
        step(
            "hq",
            "have",
            (5, 7),
            name="hq",
            claim=text("q"),
            goal={"target": text("q ∧ p"), "hypotheses": [{"name": "hq", "type": text("q")}]},
            children=[
                step(
                    "hq.s1",
                    "obtain",
                    (6, 6),
                    goal={"target": text("q"), "hypotheses": [{"name": "hq", "type": text("q")}]},
                ),
            ],
        ),
        step(
            "hp",
            "have",
            (8, 8),
            name="hp",
            claim=text("p"),
            goal={"target": text("q ∧ p"), "hypotheses": [{"name": "hp", "type": text("p")}]},
            closed_by=("automation", ["simp"]),
            mathlib=[
                {
                    "name": "And.left",
                    "doc": AND_LEFT_DOC,
                    # A tag on a core lemma is test data, not a claim about the Stacks project.
                    "tags": [{"database": "stacks", "tag": STACKS_TAG}],
                }
            ],
        ),
        step(
            "s3",
            "show",
            (9, 10),
            claim=text(UNRELIABLE_TEXT, printed="unreliable"),
            closed_by=("term", []),
            mathlib=[{"name": "And.intro", "doc": None, "tags": []}],
        ),
    ]


def document(
    node_id: str, path: str, digest: str, steps: list[dict[str, Any]], *, kind: str = "proof"
) -> dict[str, Any]:
    doc = {
        "schema": OUTLINE_SCHEMA,
        "target": TARGET,
        "node": node_id,
        "artifact": {"path": path, "hash": digest, "kind": kind},
        "gate": GATE,
        "steps": steps,
    }
    return dict(schemas.validate(doc, OUTLINE_SCHEMA))


def write(root: Path, doc: dict[str, Any]) -> Path:
    """The product at ``targets/<id>/outlines/<artifact-hash>.json`` (F19-R1)."""
    out = root / "targets" / str(doc["target"]) / "outlines"
    out.mkdir(exist_ok=True)
    path = out / f"{doc['artifact']['hash']}.json"
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path
