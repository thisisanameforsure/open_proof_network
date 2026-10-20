"""F28-T8 (D-12 v3.42): a node with a closure record derives proved while every input does.

The owner's question of 2026-10-15: "by construction you should be able to close parent nodes."
The join is kernel-checked by the post-merge job (``opn-close``) and recorded beside the node; the
status is derived from that record each render, never written, so it climbs the whole chain in one
pass and falls back the moment an input stops being proved. The root needs, in addition, the
statement vouching step 9 accepts.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from opn_gate import graph

TARGET = "t"
PROVED = graph.Proof(merge_commit="0" * 40, trust_base=graph.TRUST_KERNEL, attestation="")


def record(*inputs: str, statement_hash: str = "a" * 64) -> dict[str, Any]:
    return {
        "statement_hash": statement_hash,
        "link": {"kind": "route", "id": "x@1", "inputs": list(inputs)},
    }


def node(
    node_id: str, *, proved: bool = False, closure: dict[str, Any] | None = None
) -> graph.NodeFacts:
    return graph.NodeFacts(
        node_id=node_id,
        target_id=TARGET,
        path=Path(node_id),
        statement_hash="a" * 64,
        deps=(),
        origin="skeleton-hole",
        tutorial=False,
        relation=None,
        proof=PROVED if proved else None,
        override=None,
        artifact="proof" if proved else None,
        closure=closure,
    )


def chain(*, leaf_proved: bool = True) -> dict[str, graph.NodeFacts]:
    """r <- [a], a <- [b], b <- [c], c proved: records on b, a and r (each kernel-joined)."""
    return {
        "r": node("r", closure=record("a")),
        "a": node("a", closure=record("b")),
        "b": node("b", closure=record("c")),
        "c": node("c", proved=leaf_proved),
    }


def test_one_pass_closes_every_level_and_the_vouched_root() -> None:
    got = graph.derive_statuses(chain(), root="r", root_vouched=True)
    assert got == {"a": "proved", "b": "proved", "c": "proved", "r": "proved"}


def test_an_unvouched_root_stays_open_and_everything_below_closes() -> None:
    """Step 9's rule carried over: the root reads settled only with its statement vouched."""
    got = graph.derive_statuses(chain(), root="r", root_vouched=False)
    assert got["r"] == "ready"
    assert got["a"] == got["b"] == "proved"


def test_reverting_an_input_reopens_everything_above_it() -> None:
    got = graph.derive_statuses(chain(leaf_proved=False), root="r", root_vouched=True)
    assert got == {"a": "ready", "b": "ready", "c": "ready", "r": "ready"}


def test_a_record_for_another_statement_proves_nothing() -> None:
    nodes = chain()
    nodes["b"] = node("b", closure=record("c", statement_hash="f" * 64))
    got = graph.derive_statuses(nodes, root="r", root_vouched=True)
    assert got["b"] == got["a"] == got["r"] == "ready"


def test_an_input_that_is_not_a_node_proves_nothing() -> None:
    nodes = chain()
    nodes["b"] = node("b", closure=record("c", "gone"))
    assert graph.derive_statuses(nodes, root="r", root_vouched=True)["b"] == "ready"


def test_records_that_reach_back_prove_nothing() -> None:
    nodes = {"r": node("r", closure=record("a")), "a": node("a", closure=record("r"))}
    assert graph.derive_statuses(nodes, root="r", root_vouched=True) == {"a": "ready", "r": "ready"}


def test_a_merged_proof_still_proves_without_any_record() -> None:
    nodes = {"r": node("r", proved=True)}
    assert graph.derive_statuses(nodes, root="r", root_vouched=False) == {"r": "proved"}
