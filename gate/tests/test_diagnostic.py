"""F00 §6, §7: the structured diagnostic and its size budget — truncation never fails."""

from __future__ import annotations

import json

import pytest

from opn_gate import diagnostic
from opn_gate.diagnostic import TRUNCATION_MARKER, Diagnostic


def size(doc: dict[str, object]) -> int:
    return len(json.dumps(doc, ensure_ascii=False).encode("utf-8"))


def test_as_dict_omits_empty_details_and_is_plain_data() -> None:
    d = Diagnostic("code", "message")
    assert d.as_dict() == {"code": "code", "message": "message"}
    with_details = Diagnostic("code", "message", {"path": "a/b", "n": 1})
    assert with_details.as_dict() == {
        "code": "code",
        "message": "message",
        "details": {"path": "a/b", "n": 1},
    }
    assert "truncated" not in with_details.as_dict(max_bytes=8192)


def test_small_document_is_returned_untouched() -> None:
    doc = {"code": "c", "message": "m", "details": {"x": "y" * 10}}
    assert diagnostic.truncate(doc, 8192) is doc


@pytest.mark.parametrize("max_bytes", [8192, 512, 100, 40, 1])
def test_truncation_fits_or_bottoms_out_with_a_marker(max_bytes: int) -> None:
    """The budget is honoured whenever it can be; when it cannot (a budget smaller than the
    keys themselves) the result is still marked truncated and no exception escapes."""
    huge = Diagnostic(
        "kernel-replay-failed",
        "x" * 50_000,
        {"output": "y" * 100_000, "messages": [{"text": "z" * 5_000, "line": 3}], "n": 7},
    )
    out = huge.as_dict(max_bytes)
    assert out["truncated"] is True
    assert out["details"]["n"] == 7 and out["details"]["messages"][0]["line"] == 3
    assert out["message"].endswith(TRUNCATION_MARKER)
    assert out["details"]["messages"][0]["text"].endswith(TRUNCATION_MARKER)
    if max_bytes >= 512:
        assert size(out) <= max_bytes
        assert out["code"] == "kernel-replay-failed"
    else:  # the floor: every string is clipped to at most 16 bytes plus the marker
        assert all(
            len(s.encode("utf-8")) <= 16 + len(TRUNCATION_MARKER.encode("utf-8"))
            for s in (out["message"], out["details"]["output"])
        )


@pytest.mark.xfail(
    strict=True,
    reason="truncate clips every string leaf including `code`, so under a budget below ~300 "
    "bytes (any positive OPN_DIAGNOSTIC_MAX_BYTES is accepted, C6) the structured code becomes "
    "'kernel-replay-fa…[truncated]' — no longer the identifier D-34 names, and no longer "
    "matching attestation/v4's ^[a-z][a-z0-9-]*$ (see test_attestation)",
)
def test_the_code_survives_any_budget() -> None:
    huge = Diagnostic("kernel-replay-failed", "x" * 50_000, {"output": "y" * 100_000})
    for max_bytes in (300, 100, 1):
        assert huge.as_dict(max_bytes)["code"] == "kernel-replay-failed", max_bytes


def test_clipping_never_splits_a_multibyte_character() -> None:
    d = Diagnostic("c", "∀" * 10_000)  # three bytes each
    out = d.as_dict(200)
    assert out["truncated"] is True
    clipped = out["message"].removesuffix(TRUNCATION_MARKER)
    assert set(clipped) == {"∀"}
    assert size(out) <= 200


def test_truncated_diagnostic_is_still_valid_json_data() -> None:
    d = Diagnostic("c", "m" * 20_000, {"nested": [["a" * 3_000], {"k": "v" * 3_000}]})
    out = d.as_dict(1_000)
    json.dumps(out)  # serialisable
    assert isinstance(out["details"]["nested"][0], list)
    assert out["details"]["nested"][1]["k"].endswith(TRUNCATION_MARKER)
