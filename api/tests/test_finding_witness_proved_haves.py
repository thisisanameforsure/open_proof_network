"""F07-T44 (D-29 v3.22): the fast check asks a hole's witness what step 7 asks it.

A hole's ``META.yaml`` records which binders of its statement the merged assembly proved
(``proved_binders``, ``meta/v5``), and step 7 then holds the witness only to the rest. The service
has no Lean: witness mode (F13-T14) and the proposal pre-flight (F13-T16) send the checker the
gate's own ``WitnessType.lean`` with a few lines that ask it the question. So the record has to
reach those lines, or a contributor is told to exhibit facts the gate would discharge — and a
witness that step 7 takes is called a mismatch.
"""

from __future__ import annotations

import asyncio
from typing import Any

import yaml
from api_fakes import FakeAxle
from mcp_client import NODE, NODE_DIR, TARGET, meta
from test_check_witness_mode import STATEMENT, WITNESS, answer
from test_checks import harness_with, post, seed

from opn_api import checks

PROVED = [4, 5]
NARROWED = "OpnGate.expectedWitnessTypeNarrowed s.type #[4, 5]"


def sent_for(record: list[int] | None, content: str = WITNESS) -> str:
    h = harness_with(axle=FakeAxle(replies=[answer(None)]))
    seed(h, statement=STATEMENT)
    doc: dict[str, Any] = meta()
    if record is not None:
        doc.update(schema="meta/v5", origin="compiler-derived", proved_binders=record)
    h.githost.files[NODE_DIR + "META.yaml"] = yaml.safe_dump(doc).encode()
    h.context.files.clear()
    r = post(h, {"target_id": TARGET, "node_id": NODE, "mode": "witness", "content": content})
    assert r.status_code == 200, r.text
    (call,) = h.axle.calls
    return str(call.content)


def test_witness_mode_passes_the_holes_record() -> None:
    sent = sent_for(PROVED)
    assert NARROWED in sent
    # The narrowed function is the gate's own, sent with the file it lives in.
    assert "def expectedWitnessTypeNarrowed" in sent


def test_without_a_record_witness_mode_asks_what_it_always_asked() -> None:
    sent = sent_for(None)
    assert "let expected ← OpnGate.expectedWitnessType s.type\n" in sent
    assert "expectedWitnessTypeNarrowed s.type" not in sent


def test_the_preflight_passes_the_record_it_is_handed() -> None:
    h = harness_with(axle=FakeAxle(replies=[answer(None)]))
    seed(h, statement=STATEMENT)
    prefix = f"targets/{TARGET}/nodes/{NODE}/"
    doc = {**meta(), "schema": "meta/v5", "proved_binders": PROVED}
    files = {
        prefix + "Statement.lean": STATEMENT,
        prefix + "Witness.lean": WITNESS,
        prefix + "META.yaml": yaml.safe_dump(doc),
    }
    outcome = asyncio.run(checks.preflight_witness(h.context, "someone", TARGET, NODE, files))
    assert outcome == checks.PREFLIGHT_INCONCLUSIVE  # the fake checker ran no program
    (call,) = h.axle.calls
    assert NARROWED in call.content


def test_the_record_is_read_as_the_gate_reads_it() -> None:
    assert checks.proved_binders_of(yaml.safe_dump({"proved_binders": [5, 4]})) == (4, 5)
    for text in (None, "", "schema: meta/v4\n", "proved_binders: nope\n", ": [\n"):
        assert checks.proved_binders_of(text) == ()
