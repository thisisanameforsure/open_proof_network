"""F18-T5 (R6, R7; D-31 v3.26): an annex that names its steps, and a skeleton held to them.

An annex is prose the gate never reads for truth (D-31). ``annex/v2`` lets its front matter
carry ``steps``: the outline's steps, each an identifier and a one-line summary. A skeleton that
cites a stepped annex names each hole after one of its steps, and the gate refuses one that does
not (``annex-step-missing``); a step with no hole is carried by the assembly. A matching name
shows the decomposition followed the outline's structure and nothing more: whether the Lean
means what the prose says is the kernel's and a reader's question, never this module's.

Where the check sits: the hole names are the extractor's (``opn-artifact-type`` at the end of
step 4, ``artifact-partial``'s ``holes``), and nothing earlier knows them — the gate reads no
``have`` names from text, and a regex over Lean would be a heuristic standing in for a fact. So
the refusal is step 4's last word, after the artifact rule, and before anything merges; the
post-merge writer repeats it as the backstop, as it does ``annex-uncited``.

A summary is untrusted contributor data (C9, D-28): it is carried, published and shown escaped,
and nothing here acts on its words.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from opn_gate import schemas
from opn_gate.diagnostic import Diagnostic

#: The version that may name steps; ``annex/v1`` stays valid and is never checked (R6).
STEPPED_SCHEMA = "annex/v2"
#: Where a node keeps its annexes, each named for the SHA-256 of the whole file (D-31).
ANNEX_DIR = "annex"

FRONT_MATTER_RE = re.compile(r"\A---[ \t]*\r?\n(?P<yaml>.*?)\r?\n---[ \t]*\r?\n", re.S)


@dataclass(frozen=True)
class Step:
    """One step of a stepped annex: the hole name a skeleton binds for it, and its summary."""

    id: str
    summary: str


def front_matter(text: str) -> dict[str, Any] | None:
    """The annex's YAML front matter as a mapping, or ``None`` when it has none or it is not one
    mapping (the append's own schema check refuses such a file by name)."""
    m = FRONT_MATTER_RE.match(text)
    if m is None:
        return None
    try:
        doc = yaml.safe_load(m.group("yaml"))
    except yaml.YAMLError:
        return None
    return doc if isinstance(doc, dict) else None


def duplicate_step_ids(doc: dict[str, Any]) -> list[str]:
    """Every step id a record's ``steps`` names more than once, in first-seen order. JSON Schema
    cannot say that the ids of a list of objects are unique, so the gate and the service ask
    this beside the schema."""
    raw = doc.get("steps")
    if not isinstance(raw, list):
        return []
    seen: set[str] = set()
    dup: list[str] = []
    for item in raw:
        sid = item.get("id") if isinstance(item, dict) else None
        if not isinstance(sid, str):
            continue
        if sid in seen and sid not in dup:
            dup.append(sid)
        seen.add(sid)
    return dup


def steps_of(text: str) -> tuple[Step, ...] | None:
    """The steps a stepped annex names, in its order, or ``None`` for an annex that names none:
    a v1 annex, a v2 annex without ``steps``, or one whose front matter does not satisfy
    ``annex/v2`` (refused as an append by the schema check, so never on a merged node)."""
    doc = front_matter(text)
    if doc is None or doc.get("schema") != STEPPED_SCHEMA or "steps" not in doc:
        return None
    if schemas.violations(doc, STEPPED_SCHEMA) or duplicate_step_ids(doc):
        return None
    return tuple(Step(str(s["id"]), str(s["summary"])) for s in doc["steps"])


def steps_at(node_dir: Path, digest: str) -> tuple[Step, ...] | None:
    """The steps of the annex ``digest`` on the node, or ``None`` (absent, unreadable, v1)."""
    path = node_dir / ANNEX_DIR / f"{digest}.md"
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    return steps_of(text)


def check_steps(
    steps: Sequence[Step] | None, holes: Sequence[str], *, annex: str
) -> Diagnostic | None:
    """R6: ``annex-step-missing`` unless every hole name is a step id; ``None`` for an annex
    that names no steps (v1 is unchecked), and a step with no hole is fine."""
    if steps is None:
        return None
    ids = [s.id for s in steps]
    known = set(ids)
    missing = [h for h in holes if h not in known]
    if not missing:
        return None
    return Diagnostic(
        "annex-step-missing",
        f"the skeleton cites annex {annex[:12]}…, which names its steps ("
        + ", ".join(ids)
        + "); a hole of a skeleton that follows a stepped annex is named after one of its "
        "steps, and "
        + ", ".join(missing)
        + (" is" if len(missing) == 1 else " are")
        + " not. Rename the hole to the step it proves, or cite an annex whose steps it follows "
        "(D-31 v3.26)",
        {"annex": annex, "missing": missing, "steps": ids},
    )
