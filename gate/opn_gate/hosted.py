"""The hosted fast checker's mapping (F13-R2): ``gate/hosted-checkers.yaml``, read once.

Network configuration, not a gate check: no step imports this module, and no verdict depends on
it (D-1). It lives in ``opn_gate`` because both of its readers — the api's ``POST /check`` and
``GET /hosted-checkers.json``, and the site's target page — already import this package, and
because the file sits beside ``schemas/`` both in the repository and at the Lambda package root,
which is exactly where ``schemas.SCHEMAS_DIR`` already points (F13-T4's package rehearsal).
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml

from opn_gate import schemas

MAPPING_PATH = schemas.SCHEMAS_DIR.parent / "hosted-checkers.yaml"
MAPPING_SCHEMA = "hosted-checkers/v1"
SERVICE = "axle"  # the one service the mapping may name (F13-Q5)


class MappingError(ValueError):
    """The mapping is missing, unreadable, or not ``hosted-checkers/v1``; the message names it."""


@dataclass(frozen=True)
class Hosted:
    """One pin's entry: its Mathlib tag, the hosted environment or ``None``, whether that
    environment is exact, and what differs when it is not."""

    mathlib_tag: str
    environment: str | None
    exact: bool
    note: str | None


@lru_cache(maxsize=4)
def load(path: Path = MAPPING_PATH) -> dict[str, Hosted]:
    """Pin sha -> entry. Cached per path for the life of the process: the file changes only with
    a network commit, which is a new deploy or a new site build."""
    try:
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        msg = f"{path.name}: {exc}"
        raise MappingError(msg) from exc
    if not isinstance(doc, dict) or doc.get("schema") != MAPPING_SCHEMA:
        msg = f"{path.name} is not {MAPPING_SCHEMA}"
        raise MappingError(msg)
    if doc.get("service") != SERVICE:
        msg = f"{path.name} names service {doc.get('service')!r}; only {SERVICE!r} is known"
        raise MappingError(msg)
    out: dict[str, Hosted] = {}
    for sha, entry in (doc.get("pins") or {}).items():
        if not isinstance(entry, dict):
            msg = f"{path.name}: the entry for {sha} is not a mapping"
            raise MappingError(msg)
        environment = entry.get("environment")
        note = entry.get("note")
        out[str(sha)] = Hosted(
            mathlib_tag=str(entry.get("mathlib_tag")),
            environment=str(environment) if environment is not None else None,
            exact=bool(entry.get("exact")),
            note=str(note) if note is not None else None,
        )
    return out
