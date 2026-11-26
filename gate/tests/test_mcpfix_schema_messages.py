"""mcpfix (lead; verifier VB, N1, 2026-11-25): a schema violation's message writes the values it
quotes as JSON, wherever it is read.

The MCP adapter learned to say ``null is not of type 'object'`` (WA1), but ``POST /submissions``
still answered ``$['automation']['method']: None is not one of ['manual', ...]`` and
``True is not of type 'string'``: the routes read the gate's ``schemas.violations``, which passed
the validator's Python wording through."""

from __future__ import annotations

from opn_gate import schemas, submission


def test_violations_quote_values_as_json() -> None:
    doc = {
        "schema": submission.SCHEMA,
        "automation": {"method": None, "models": [True], "framework": "f"},
    }
    messages = " ".join(v.message for v in schemas.violations(doc, submission.SCHEMA))
    assert "None" not in messages and "True is not" not in messages
    assert "null is not one of" in messages
    assert "true is not of type 'string'" in messages
    assert "['manual'" not in messages
