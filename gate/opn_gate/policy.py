"""The graph's ``policy.json`` (F15-R3, Q2; D-32 v3.17, D-35).

One file at the graph root, curator-owned, carrying the one switch the steward rule has: whether
an open-track target with no active steward refuses claims. Absent, the rule is not enforced —
which is the state every graph is in until the calibration run passes (Stages v3.17) — and its
state is published at the top of ``targets/index.json`` so an agent and the site read the same
fact. Flipping it either way is one visible pull request naming the evidence; a re-pin never
changes it, which is why the switch is a file and not a gate commit (F15-Q2).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from opn_gate import schemas

FILE = "policy.json"
SCHEMA = "policy/v1"


@dataclass(frozen=True)
class Policy:
    """The steward rule's state. ``present`` says whether the graph holds the file at all."""

    enforced: bool = False
    since: str | None = None
    evidence: str | None = None
    present: bool = False

    def as_dict(self) -> dict[str, Any]:
        """The shape ``targets/index.json`` publishes (``targets-index/v6``)."""
        return {
            "steward_rule": {
                "enforced": self.enforced,
                "since": self.since,
                "evidence": self.evidence,
            }
        }


def policy_path(graph_root: Path) -> Path:
    return graph_root / FILE


def load(graph_root: Path) -> Policy:
    """The graph's policy, or the default when there is no file. A file that does not validate
    is a graph defect and raises ``SchemaError``: the file reaches the tree only through a
    curator's merge, and a rule read off a malformed switch would be a guess (C7)."""
    path = policy_path(graph_root)
    if not path.is_file():
        return Policy()
    doc = schemas.load_json(path, SCHEMA)
    rule = doc["steward_rule"]
    return Policy(
        enforced=bool(rule["enforced"]),
        since=rule.get("since"),
        evidence=rule.get("evidence"),
        present=True,
    )


def document(*, enforced: bool, since: str | None, evidence: str | None) -> dict[str, Any]:
    """A validated ``policy/v1`` document, for the curator's switch pull request (F15-T15)."""
    return schemas.validate(
        {
            "schema": SCHEMA,
            "steward_rule": {"enforced": enforced, "since": since, "evidence": evidence},
        },
        SCHEMA,
    )


def write(graph_root: Path, doc: dict[str, Any]) -> Path:
    path = policy_path(graph_root)
    path.write_bytes(schemas.canonical_json(schemas.validate(doc, SCHEMA)))
    return path
