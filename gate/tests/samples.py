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
        "schema": "attestation/v4",
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
        "submitter": None,
        "model_and_tooling": "undeclared",
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


def revision_request(**overrides: Any) -> dict[str, Any]:
    doc: dict[str, Any] = {
        "schema": "revision-request/v1",
        "node": "tutorial-and-swap",
        "contributor": "thisisanameforsure",
        "defect_class": "missing-hypothesis",
        "evidence": {
            "text": "the statement holds vacuously when p is False; a hypothesis is missing",
            "exhibit": "example : True := trivial\n",
        },
        "date": "2026-09-10",
    }
    doc.update(overrides)
    return doc


def defect_claim(**overrides: Any) -> dict[str, Any]:
    doc: dict[str, Any] = {
        "schema": "defect-claim/v1",
        "stmt_ref": "tutorial-and-swap",
        "class": "junk-value",
        "line": 3,
        "exhibit": "example : True := trivial\n",
        "contributor": "thisisanameforsure",
        "date": "2026-09-10",
    }
    doc.update(overrides)
    return doc


def screen_finding(**overrides: Any) -> dict[str, Any]:
    """A ``defect-claim/v2`` claim as the QA screen files one (F12-R4, Q7)."""
    doc: dict[str, Any] = {
        "schema": "defect-claim/v2",
        "stmt_ref": "tutorial-and-swap",
        "class": "screen-finding",
        "line": 1,
        "exhibit": "example : True := trivial\n",
        "contributor": "opn-gate-qa",
        "date": "2026-09-12",
        "qa_exhibit": "targets/propositional/qa/exhibits/root-screen-false-1.lean",
        "readings": ["misformalization", "refutation"],
        "routes": None,
        "note": (
            "either the statement is a misformalization (D-8) or the conjecture is refuted (D-12)"
        ),
    }
    doc.update(overrides)
    return doc


def qa_record(**overrides: Any) -> dict[str, Any]:
    """A ``qa/v1`` record: one clean run of the screens (F12-R1)."""
    row = {
        "check": "compile",
        "kind": "exhibit",
        "tool": "opn-gate qa screen",
        "tool_version": "0.0.0",
        "model": None,
        "model_version": None,
        "verdict": "pass",
        "exhibit": None,
        "exhibit_sha256": None,
        "timestamp": "2026-09-12T10:00:00Z",
    }
    doc: dict[str, Any] = {
        "schema": "qa/v1",
        "subject": "root",
        "statement_hash": SHA256,
        "lean_toolchain": "leanprover/lean4:v4.33.1",
        "mathlib_sha": None,
        "date": "2026-09-12T10:00:00Z",
        "produced_by": "opn-gate qa screen",
        "checks": [row, {**row, "check": "screen-statement"}],
    }
    doc.update(overrides)
    return doc


def target_status(**overrides: Any) -> dict[str, Any]:
    doc: dict[str, Any] = {
        "schema": "target-status/v2",
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


def target_record(**overrides: Any) -> dict[str, Any]:
    """A ``target/v1`` intake record with every D-6 artifact present (F11-R1)."""
    doc: dict[str, Any] = {
        "schema": "target/v1",
        "id": "euclid-primes",
        "title": "Euclid's theorem",
        "informal": "For every natural number n there is a prime greater than n.",
        "track": "formalization",
        "source": {"kind": "other", "ref": "Euclid, Elements IX.20", "url": None},
        "curator": "curator",
        "prior_art": {
            "arxiv_query": None,
            "forum_url": None,
            "summary": "Classical; the argument is Euclid's and is not in dispute.",
        },
        "library_coverage": {"mathlib_sha": "a" * 40, "missing_prerequisites": []},
        "provenance": {
            "statement_source": "other",
            "author": "author",
            "adversarially_reviewed": False,
            "upstream_commit": None,
        },
        "sources": [],
        "attack_routes": [],
        "posting": None,
        "domains": ["number-theory"],
    }
    doc.update(overrides)
    return doc


def fidelity_certificate(**overrides: Any) -> dict[str, Any]:
    """A ``fidelity/v1`` certificate (F11-R3; D-9 v3.12)."""
    doc: dict[str, Any] = {
        "schema": "fidelity/v1",
        "subject": "root",
        "grade": "screened-and-signed",
        "subject_author": "author",
        "attestor": "reviewer",
        "date": "2026-09-11",
        "evidence": "Read the Lean statement against the informal one; they agree.",
    }
    doc.update(overrides)
    return doc
