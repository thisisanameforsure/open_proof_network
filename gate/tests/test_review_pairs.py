"""F26-T6: pairs — two-layer matching, the degenerate guard, refutation by instance (R7, R8; AC5).

Fast tier, the toolchain seam's fake. The pairs are the first prototype's Legendre candidates:
the faithful reading, the closed interval (equivalent to it only because squares are never prime,
so weaker as a formula) and a rewording.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml
from review_support import Model, ReviewFake, legendre, make_graph, prototype_lean, tree
from test_review_job import TARGET, exhibits, run_job

from opn_gate import review, review_pairs


def pairs(graph: Path) -> list[dict[str, Any]]:
    folder = graph / "targets" / TARGET / "review" / "pairs"
    return [yaml.safe_load(p.read_text()) for p in sorted(folder.glob("*.yaml"))]


def two(tmp_path: Path, other: str) -> tuple[Path, str, str]:
    graph, ids = make_graph(
        tmp_path,
        candidates={
            "faithful": prototype_lean("legendre", "human-ref"),
            "other": prototype_lean("legendre", other),
        },
    )
    return graph, ids["faithful"], ids["other"]


def direction(doc: dict[str, Any], a: str, b: str) -> dict[str, Any]:
    """The record's direction ``a → b``."""
    found: dict[str, Any] = doc["forward"] if (doc["a"], doc["b"]) == (a, b) else doc["backward"]
    return found


def test_the_degenerate_guard_keeps_a_direction_open(tmp_path: Path) -> None:
    """AC5: a proof that never uses its hypothesis (it still proves with the hypothesis cleared)
    is refused as a proof of equivalence; the direction stays open with the reason."""
    graph, a, b = two(tmp_path, "alt-mul")
    fake = ReviewFake(
        models={a: Model(legendre()), b: Model(legendre())},
        implies={(a, b), (b, a)},
        trivial={b},  # b's claim follows from nothing: the bounded proof never needs a
    )
    run_job(graph, fake, tmp_path)
    (doc,) = pairs(graph)
    d = direction(doc, a, b)
    assert d["state"] == "open"
    assert d["exhibit"] is None
    assert d["attempt"]["who"] == "gate"
    assert "degenerate guard" in d["attempt"]["tool"]
    guard = [e for e in exhibits(graph) if e["kind"] == "pair" and e["candidate"] == a]
    assert [(e["result"], e["test"]) for e in guard] == [("open", b)]
    assert "never uses it" in guard[0]["detail"]
    lean = (graph / "targets" / TARGET / "review" / "exhibits" / guard[0]["lean_file"]).read_text()
    assert "clear h" in lean
    # the other direction used its hypothesis and is proved: so no cluster
    assert direction(doc, b, a)["state"] == "proved"
    assert not review.equivalent(doc)


def test_a_refutation_names_its_instance(tmp_path: Path) -> None:
    """AC5: refuted is an instance the kernel checked — here n = 1 with 1 the only prime, where
    the closed interval holds and the open one fails."""
    graph, a, b = two(tmp_path, "alt-closed")
    fake = ReviewFake(
        models={a: Model(legendre()), b: Model(legendre(closed=True))}, implies={(a, b)}
    )
    run_job(graph, fake, tmp_path)
    (doc,) = pairs(graph)
    assert direction(doc, a, b)["state"] == "proved"
    back = direction(doc, b, a)
    assert back["state"] == "refuted" and back["attempt"] is None
    (e,) = [x for x in exhibits(graph) if x["id"] == back["exhibit"]]
    assert (e["kind"], e["result"], e["candidate"], e["test"]) == ("pair", "refuted", b, a)
    assert "n = 1, supposing 1 were the only prime" in e["detail"]
    lean = (graph / "targets" / TARGET / "review" / "exhibits" / e["lean_file"]).read_text()
    assert "decide +kernel" in lean and "∧ ¬" in lean


def test_a_failed_attempt_is_never_refuted(tmp_path: Path) -> None:
    """AC5 / D-9 v3.12: the tables say the two differ, the kernel refuses the instance, and the
    direction is open, not refuted; no exhibit says refuted."""
    graph, a, b = two(tmp_path, "alt-closed")
    fake = ReviewFake(
        models={a: Model(legendre()), b: Model(legendre(closed=True))},
        implies={(a, b)},
        kernel_refuses={
            json.dumps({"concept": "prime", "n": 1, "probe": "witness", "set": [1]}, sort_keys=True)
        },
    )
    run_job(graph, fake, tmp_path)
    (doc,) = pairs(graph)
    back = direction(doc, b, a)
    assert back["state"] == "open"
    assert back["attempt"] == {"who": "gate", "tool": review_pairs.TOOL, "budget_s": 5}
    assert not [e for e in exhibits(graph) if e["result"] == "refuted"]


def test_no_proof_and_no_instance_is_open(tmp_path: Path) -> None:
    graph, a, b = two(tmp_path, "alt-mul")
    fake = ReviewFake(models={a: Model(legendre()), b: Model(legendre())})
    run_job(graph, fake, tmp_path)
    (doc,) = pairs(graph)
    assert doc["forward"]["state"] == doc["backward"]["state"] == "open"


def test_both_directions_proved_make_one_cluster(tmp_path: Path) -> None:
    graph, a, b = two(tmp_path, "alt-mul")
    fake = ReviewFake(models={a: Model(legendre()), b: Model(legendre())}, implies={(a, b), (b, a)})
    summary = run_job(graph, fake, tmp_path)
    (doc,) = pairs(graph)
    assert review.equivalent(doc)
    assert (doc["a"], doc["b"]) == tuple(sorted([a, b]))
    assert summary["clusters"] == [sorted([a, b])]


def test_pairs_are_not_attempted_again(tmp_path: Path) -> None:
    """R13: a second run neither re-attempts a settled or same-budget open direction nor
    writes a pair record."""
    graph, a, b = two(tmp_path, "alt-closed")
    fake = ReviewFake(
        models={a: Model(legendre()), b: Model(legendre(closed=True))}, implies={(a, b)}
    )
    run_job(graph, fake, tmp_path)
    before, n = tree(graph), len(fake.texts)
    run_job(graph, fake, tmp_path)
    assert tree(graph) == before
    heads = [t.split("\n", 1)[0] for t in fake.texts[n:]]
    assert not [h for h in heads if '"op": "direction"' in h or '"op": "link"' in h]
