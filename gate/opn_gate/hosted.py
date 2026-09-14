"""The hosted fast checker's mapping (F13-R2): ``gate/hosted-checkers.yaml``, read once.

Network configuration, not a gate check: no step imports this module, and no verdict depends on
it (D-1). It lives in ``opn_gate`` because both of its readers — the api's ``POST /check`` and
``GET /hosted-checkers.json``, and the site's target page — already import this package, and
because the file sits beside ``schemas/`` both in the repository and at the Lambda package root,
which is exactly where ``schemas.SCHEMAS_DIR`` already points (F13-T4's package rehearsal).

Two kinds of entry: ``pins`` maps a pinned Mathlib commit to its environment, and ``core`` is
the one environment for a graph that pins no Mathlib, whose statements are Lean core only (the
tutorial, F13-Q9). ``lookup`` chooses between them from a target's ``mathlib_sha``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from opn_gate import schemas

MAPPING_PATH = schemas.SCHEMAS_DIR.parent / "hosted-checkers.yaml"
MAPPING_SCHEMA = "hosted-checkers/v1"
SERVICE = "axle"  # the one service the mapping may name (F13-Q5)


class MappingError(ValueError):
    """The mapping is missing, unreadable, or not ``hosted-checkers/v1``; the message names it."""


@dataclass(frozen=True)
class Hosted:
    """One entry: its Mathlib tag (``None`` for the core entry), the hosted environment or
    ``None``, whether that environment is exact, and what differs when it is not."""

    mathlib_tag: str | None
    environment: str | None
    exact: bool
    note: str | None


@dataclass(frozen=True)
class HostedMapping:
    pins: dict[str, Hosted] = field(default_factory=dict)
    core: Hosted | None = None


def _entry(path: Path, where: str, raw: Any) -> Hosted:
    if not isinstance(raw, dict):
        msg = f"{path.name}: the entry for {where} is not a mapping"
        raise MappingError(msg)
    tag, environment, note = raw.get("mathlib_tag"), raw.get("environment"), raw.get("note")
    return Hosted(
        mathlib_tag=str(tag) if tag is not None else None,
        environment=str(environment) if environment is not None else None,
        exact=bool(raw.get("exact")),
        note=str(note) if note is not None else None,
    )


@lru_cache(maxsize=4)
def load(path: Path = MAPPING_PATH) -> HostedMapping:
    """The whole mapping. Cached per path for the life of the process: the file changes only with
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
    pins = {str(sha): _entry(path, str(sha), raw) for sha, raw in (doc.get("pins") or {}).items()}
    core = _entry(path, "core", doc["core"]) if doc.get("core") is not None else None
    return HostedMapping(pins=pins, core=core)


def lookup(mapping: HostedMapping, mathlib_sha: str | None) -> Hosted | None:
    """The entry serving a target: its pin's, or the core entry when it pins no Mathlib."""
    if mathlib_sha is None:
        return mapping.core
    return mapping.pins.get(mathlib_sha)
