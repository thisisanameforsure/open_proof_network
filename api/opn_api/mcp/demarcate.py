"""Untrusted-data demarcation (F09-R6; D-28, D-31; C9) — the rule itself lives in the gate
package since F10-T2, because the post-merge job applies it to ``CONTEXT.json`` and the api
applies it to what it serves: one table of free-text fields, one wrapper (F10-Q6). This module
keeps the adapter's import path and re-exports every name."""

from __future__ import annotations

from opn_gate.demarcate import (
    FREE_TEXT,
    UNTRUSTED_NOTE,
    bare_strings,
    is_wrapped,
    record,
    wrap,
)

__all__ = ["FREE_TEXT", "UNTRUSTED_NOTE", "bare_strings", "is_wrapped", "record", "wrap"]
