"""The structured diagnostic every check emits (D-34; F00-R7, R18; attestation/v1 ``diagnostic``).

Plain strings only: a diagnostic quotes at most the failing line of contributor text and is
served as data, never rendered as markup (F00 §7). ``truncate`` applies the §6 size budget with
an explicit marker.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

TRUNCATION_MARKER = "…[truncated]"


@dataclass(frozen=True)
class Diagnostic:
    code: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)

    def as_dict(self, max_bytes: int | None = None) -> dict[str, Any]:
        out: dict[str, Any] = {"code": self.code, "message": self.message}
        if self.details:
            out["details"] = self.details
        if max_bytes is not None:
            out = truncate(out, max_bytes)
        return out


def truncate(doc: dict[str, Any], max_bytes: int) -> dict[str, Any]:
    """Shrink string leaves until the JSON form fits ``max_bytes``; mark the result truncated."""
    import json  # noqa: PLC0415 — tiny helper; keeps the module import-light

    def size(d: dict[str, Any]) -> int:
        return len(json.dumps(d, ensure_ascii=False).encode("utf-8"))

    if size(doc) <= max_bytes:
        return doc
    out = dict(doc)
    out["truncated"] = True
    budget = max(64, max_bytes // 4)
    while size(out) > max_bytes and budget >= 16:
        out = _clip_strings(out, budget)
        budget //= 2
    return out


def _clip_strings(value: Any, budget: int) -> Any:
    if isinstance(value, str):
        if len(value.encode("utf-8")) > budget:
            clipped = value.encode("utf-8")[:budget].decode("utf-8", errors="ignore")
            return clipped + TRUNCATION_MARKER
        return value
    if isinstance(value, dict):
        return {k: _clip_strings(v, budget) for k, v in value.items()}
    if isinstance(value, list):
        return [_clip_strings(v, budget) for v in value]
    return value
