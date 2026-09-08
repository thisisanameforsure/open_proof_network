"""Valid sample documents for the current schemas, for tests to start from and mutate."""

from __future__ import annotations

from typing import Any

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
