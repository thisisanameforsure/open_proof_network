"""Schema registry and validation (F00-R9, R10; D-34).

Every schema lives at ``gate/schemas/<name>/v<n>.json`` and is identified by the string
``"<name>/v<n>"`` a document carries in its ``schema`` field. A published schema is never edited:
``gate/schemas/HASHES`` pins each file's sha256 and the test suite fails if one drifts.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Any

import jsonschema
import yaml

SCHEMAS_DIR = Path(__file__).resolve().parents[1] / "schemas"
HASHES_FILE = SCHEMAS_DIR / "HASHES"
_SCHEMA_ID_RE = re.compile(r"^(?P<name>[a-z][a-z0-9-]*)/v(?P<version>[1-9][0-9]*)$")

JsonDoc = dict[str, Any]


class SchemaError(ValueError):
    """A document is malformed, names an unknown schema, or fails validation."""


@dataclass(frozen=True)
class Violation:
    path: str
    message: str


def content_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def schema_path(schema_id: str) -> Path:
    m = _SCHEMA_ID_RE.match(schema_id)
    if not m:
        msg = f"malformed schema id {schema_id!r} (expected <name>/v<n>)"
        raise SchemaError(msg)
    return SCHEMAS_DIR / m.group("name") / f"v{m.group('version')}.json"


def known_schemas() -> tuple[str, ...]:
    return tuple(
        sorted(f"{p.parent.name}/{p.stem}" for p in SCHEMAS_DIR.glob("*/v*.json") if p.is_file())
    )


@cache
def load_schema(schema_id: str) -> JsonDoc:
    path = schema_path(schema_id)
    if not path.is_file():
        msg = f"unknown schema {schema_id!r}; known: {', '.join(known_schemas())}"
        raise SchemaError(msg)
    doc: JsonDoc = json.loads(path.read_bytes())
    return doc


@cache
def _validator(schema_id: str) -> jsonschema.Draft202012Validator:
    schema = load_schema(schema_id)
    # No format checker: jsonschema's date-time/uri checks need extra packages (C5), so the
    # schemas constrain those fields with explicit patterns instead.
    return jsonschema.Draft202012Validator(schema)


def violations(doc: object, schema_id: str | None = None) -> list[Violation]:
    """Validate ``doc`` against the schema in its ``schema`` field (or ``schema_id``)."""
    if not isinstance(doc, dict):
        return [Violation("$", f"document must be an object, got {type(doc).__name__}")]
    sid = schema_id if schema_id is not None else doc.get("schema")
    if not isinstance(sid, str):
        return [Violation("$.schema", "missing or non-string schema field")]
    try:
        validator = _validator(sid)
    except SchemaError as exc:
        return [Violation("$.schema", str(exc))]
    found = sorted(validator.iter_errors(doc), key=lambda e: list(e.absolute_path))
    return [Violation("$" + "".join(f"[{p!r}]" for p in e.absolute_path), e.message) for e in found]


def validate(doc: object, schema_id: str | None = None) -> JsonDoc:
    """Return ``doc`` if it validates, else raise ``SchemaError`` listing every violation."""
    found = violations(doc, schema_id)
    if found:
        what = schema_id or (doc.get("schema") if isinstance(doc, dict) else None)
        lines = "; ".join(f"{v.path}: {v.message}" for v in found)
        msg = f"document does not satisfy {what!r}: {lines}"
        raise SchemaError(msg)
    assert isinstance(doc, dict)  # narrowed by violations()
    return doc


def load_json(path: Path, schema_id: str | None = None) -> JsonDoc:
    try:
        doc = json.loads(path.read_bytes())
    except (OSError, json.JSONDecodeError) as exc:
        msg = f"cannot read JSON {path}: {exc}"
        raise SchemaError(msg) from exc
    return validate(doc, schema_id)


def load_yaml(path: Path, schema_id: str | None = None) -> JsonDoc:
    try:
        doc: object = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        msg = f"cannot read YAML {path}: {exc}"
        raise SchemaError(msg) from exc
    return validate(doc, schema_id)


def canonical_json(doc: JsonDoc) -> bytes:
    """The one serialization every record uses, so hashes and D-5 comparisons are stable."""
    return (json.dumps(doc, sort_keys=True, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


# --- pinned hashes (R10) ---------------------------------------------------------------------


def compute_hashes(schemas_dir: Path = SCHEMAS_DIR) -> dict[str, str]:
    return {
        f"{p.parent.name}/{p.name}": content_hash(p.read_bytes())
        for p in sorted(schemas_dir.glob("*/v*.json"))
    }


def read_pins(hashes_file: Path = HASHES_FILE) -> dict[str, str]:
    pins: dict[str, str] = {}
    for raw in hashes_file.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        digest, _, name = line.partition("  ")
        pins[name.strip()] = digest.strip()
    return pins


def verify_pins(schemas_dir: Path = SCHEMAS_DIR, hashes_file: Path = HASHES_FILE) -> list[str]:
    """Return a list of problems; empty means every published schema matches its pin."""
    actual = compute_hashes(schemas_dir)
    pinned = read_pins(hashes_file)
    problems = [f"schema {name} is not pinned in HASHES" for name in actual if name not in pinned]
    problems += [
        f"pinned schema {name} is missing on disk" for name in pinned if name not in actual
    ]
    problems += [
        f"schema {name} was edited: pinned {pinned[name][:12]}…, actual {actual[name][:12]}…"
        for name in actual
        if name in pinned and pinned[name] != actual[name]
    ]
    return problems
