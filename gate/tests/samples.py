"""Valid sample documents for the current schemas, for tests to start from and mutate."""

from __future__ import annotations

from typing import Any

import yaml

SHA1 = "0123456789abcdef0123456789abcdef01234567"
SHA256 = "a" * 64


def gate_spec(**overrides: Any) -> dict[str, Any]:
    doc: dict[str, Any] = {
        "schema": "gate-spec/v1",
        "graph_id": "propositional",
        "lean_toolchain": "leanprover/lean4:v4.33.1",
        "mathlib_sha": None,
        "axiom_allowlist": ["propext", "Classical.choice", "Quot.sound"],
        "hazard_checkers": [],
        "olean_cache_url": None,
        "devcontainer_ref": None,
        "network_commit": SHA1,
        "step3_caps": {"cpu": 2, "memory_mib": 4096, "wallclock_s": 600},
        "accepted_precheck_signatures": ["service", "contributor", "none"],
        "precheck_max_age_s": 86400,
        "gate_owner": "thisisanameforsure",
    }
    doc.update(overrides)
    return doc


def meta(**overrides: Any) -> dict[str, Any]:
    doc: dict[str, Any] = {
        "schema": "meta/v1",
        "id": "tutorial-and-swap",
        "status": "ready",
        "deps": [],
        "statement-hash": SHA256,
        "origin": "authored",
        "provenance": {"author": "thisisanameforsure", "model": None, "source": None},
        "tutorial": True,
    }
    doc.update(overrides)
    return doc


def attestation(**overrides: Any) -> dict[str, Any]:
    doc: dict[str, Any] = {
        "schema": "attestation/v3",
        "graph_id": "propositional",
        "node_id": "tutorial-and-swap",
        "statement_hash": SHA256,
        "lean_toolchain": "leanprover/lean4:v4.33.1",
        "toolchain_hash": "b" * 64,
        "mathlib_sha": None,
        "gate_spec_hash": "c" * 64,
        "network_commit": SHA1,
        "graph_commit": None,
        "runner": "local",
        "tooling": {"model": None, "harness": None},
        "verdict": "pass",
        "first_failing_step": None,
        "diagnostic": None,
        "steps": [
            {"step": 1, "name": "toolchain", "result": "pass", "diagnostic": None},
            {"step": 2, "name": "paths", "result": "pass", "diagnostic": None},
            {"step": 4, "name": "kernel-replay", "result": "pass", "diagnostic": None},
            {"step": 5, "name": "axioms", "result": "pass", "diagnostic": None},
        ],
        "artifact_hash": "d" * 64,
        "precheck_attestation": {"hash": None, "signature_kind": None},
        "merge_commit": None,
        "review": None,
        "trust_base": "kernel",
        "signature": {
            "kind": "none",
            "key_id": None,
            "value": None,
            "timestamp": "2026-09-08T01:23:45Z",
        },
    }
    doc.update(overrides)
    return doc


def waiver(**overrides: Any) -> dict[str, Any]:
    doc: dict[str, Any] = {
        "schema": "waiver/v1",
        "kind": "native_decide",
        "justification": "the kernel cannot reduce the 10^6-case check in reasonable time",
        "author": "thisisanameforsure",
        "date": "2026-09-09",
    }
    doc.update(overrides)
    return doc


def postmortem(**overrides: Any) -> dict[str, Any]:
    doc: dict[str, Any] = {
        "schema": "postmortem/v1",
        "node": "tutorial-and-swap",
        "contributor": "thisisanameforsure",
        "route": "strong induction on the exponent k",
        "route_class": "induction",
        "outcome": "refuted-route",
        "terminal_goal_state": "n k : Nat\nhk : 2 <= k\n|- P k",
        "failure_class": "route-dead-ends",
        "detail": "the inductive step needs a uniform bound the route cannot supply",
        "artifacts": {"missing_lemmas": ["uniform bound on the partial sums"]},
    }
    doc.update(overrides)
    return doc


def annex_front_matter(**overrides: Any) -> dict[str, Any]:
    doc: dict[str, Any] = {
        "schema": "annex/v1",
        "node": "tutorial-and-swap",
        "contributor": "thisisanameforsure",
        "licence": "CC-BY-4.0",
        "date": "2026-09-10T00:00:00Z",
        "model_and_tooling": None,
    }
    doc.update(overrides)
    return doc


def annex_file(
    body: str = "The argument runs by symmetry of conjunction.\n", **overrides: Any
) -> bytes:
    """An annex as it lands in the graph: YAML front matter, then the prose (D-31)."""
    head = yaml.safe_dump(annex_front_matter(**overrides), sort_keys=True)
    return f"---\n{head}---\n{body}".encode()


def approach_record(**overrides: Any) -> dict[str, Any]:
    doc: dict[str, Any] = {
        "schema": "approach-record/v1",
        "target": "propositional",
        "contributor": "thisisanameforsure",
        "route": "reduce every associativity obligation to a normal form and compare",
        "outcome": "exhausted",
        "pinned_mathlib_sha": None,
        "model_and_tooling": None,
        "date": "2026-09-10T00:00:00Z",
    }
    doc.update(overrides)
    return doc


def precheck_record(**overrides: Any) -> dict[str, Any]:
    doc: dict[str, Any] = {
        "schema": "precheck-record/v1",
        "node": "tutorial-and-swap",
        "statement_hash": SHA256,
        "verdict": "precheck-fail",
        "first_failing_step": 4,
        "diagnostic": {"code": "kernel-replay", "message": "the proof term does not typecheck"},
        "terminal_goal_state": "p q : Prop\nh : p /\\ q\n|- q /\\ p",
        "lean_toolchain": "leanprover/lean4:v4.33.1",
        "mathlib_sha": None,
        "gate_spec_hash": "c" * 64,
        "network_commit": SHA1,
        "tooling": {"model": None, "harness": "pregate.sh"},
        "date": "2026-09-10T00:00:00Z",
    }
    doc.update(overrides)
    return doc


def submission_meta(**overrides: Any) -> dict[str, Any]:
    doc: dict[str, Any] = {
        "schema": "submission-meta/v1",
        "submission_id": "01M23SFDNG8CTH1AD92EZ0AAPT",
        "identity": {"pseudonym": "thisisanameforsure", "proof_kind": "github"},
        "artifact_type": "proof",
        "tooling": {"model": None, "version": None, "harness": None},
    }
    doc.update(overrides)
    return doc


def node_status(**overrides: Any) -> dict[str, Any]:
    doc: dict[str, Any] = {
        "schema": "node-status/v1",
        "status": "abandoned",
        "cause": "curator: superseded by the route through and-reassoc",
        "author": "thisisanameforsure",
        "date": "2026-09-09",
    }
    doc.update(overrides)
    return doc


def target_status(**overrides: Any) -> dict[str, Any]:
    doc: dict[str, Any] = {
        "schema": "target-status/v1",
        "status": "active",
        "claimable": True,
        "fidelity": "mechanical-only",
        "author": "thisisanameforsure",
        "date": "2026-09-09",
    }
    doc.update(overrides)
    return doc


def frontier_entry(**overrides: Any) -> dict[str, Any]:
    doc: dict[str, Any] = {
        "node_id": "and-swap-reassoc",
        "target_id": "propositional",
        "statement_hash": SHA256,
        "relation": None,
        "origin": "authored",
        "tags": {"deps": ["and-reassoc", "tutorial-and-swap"], "library": []},
        "attempts": 0,
        "refuted_route_classes": [],
        "failure_class_histogram": {},
        "ready_since": "2026-09-09T00:00:00Z",
        "claims": {"active": [], "history_count": 0},
        "annex_present": False,
        "bounty": False,
        "claimable": True,
        "tutorial": False,
    }
    doc.update(overrides)
    return doc
