"""F08-T31 (D-14, D-18 v3.27): a listed curator may withdraw a status record or a defect claim.

The 2026-10-04 audit found that a status record or a defect claim could be removed only by a
direct push: every mode refuses a deletion, so ``disputed`` had no exit (the trap ``stale`` had
before v3.18) and six circularity claims filed under the pre-v3.23 direction keep four nodes off
the frontier (F08-Q33). v3.27's answer is derive, never rewrite (F08-T10): a curator files an
append-only ``withdrawal/v1`` record under the node, ``withdrawals/<stamp>-<curator>.yaml``,
naming the record (``status/<file>`` or ``defects/<file>``, relative to the same node) and a
reason. It is reviewed like any curator record (F08-R8). The withdrawn file stays in the tree,
and every reader of status records and defect claims reads it as absent.

No date is compared anywhere: a withdrawal applies because it is in the tree, never because it
is "newer" than what it names (2026-09-19, "ask who wrote the clock").
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml
from harness import TARGET, copy_graph

from opn_gate import graph, modes, paths, products, records, schemas
from opn_gate.modes import Curators
from opn_gate.paths import Change

HOLE = "and-reassoc"
ANCESTOR = "and-swap-reassoc"  # the root; it depends on the hole
NODE_DIR = f"targets/{TARGET}/nodes/{HOLE}"
CLAIM_NAME = "20260923T120000Z-alice.yaml"
CLAIM = f"{NODE_DIR}/defects/{CLAIM_NAME}"
STATUS_NAME = "20261001T090000Z-founder.yaml"
STATUS = f"{NODE_DIR}/status/{STATUS_NAME}"
WITHDRAWAL = f"{NODE_DIR}/withdrawals/20261004T120000Z-founder.yaml"
CURATORS = Curators((("founder", "founder-login"), ("second", "second-login")))
RENDERED = "5" * 40
NOW = "2026-10-04T12:00:00Z"
EXHIBIT = (
    "theorem circular :\n"
    "    (∀ p q r : Prop, (p ∧ q) ∧ r → p ∧ (q ∧ r)) →\n"
    "    ∀ p q r : Prop, (p ∧ q) ∧ r → r ∧ (q ∧ p) :=\n"
    "  fun _ _ _ _ h => ⟨h.2, h.1.2, h.1.1⟩\n"
)


def write_yaml(root: Path, rel: str, doc: dict[str, Any]) -> str:
    (root / rel).parent.mkdir(parents=True, exist_ok=True)
    (root / rel).write_text(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True), "utf-8")
    return rel


def file_claim(root: Path) -> str:
    return write_yaml(
        root,
        CLAIM,
        {
            "schema": "defect-claim/v3",
            "stmt_ref": HOLE,
            "class": "circular-decomposition",
            "ancestor": ANCESTOR,
            "line": 1,
            "exhibit": EXHIBIT,
            "contributor": "alice",
            "date": "2026-09-23",
        },
    )


def file_status(root: Path, status: str = "disputed", **extra: str) -> str:
    doc: dict[str, Any] = {
        "schema": "node-status/v1",
        "status": status,
        "cause": "a ground (ii) dispute accepted for adjudication",
        "author": "founder",
        "date": "2026-10-01",
    }
    doc.update(extra)
    return write_yaml(root, STATUS, doc)


def withdrawal_doc(withdraws: str = f"defects/{CLAIM_NAME}") -> dict[str, Any]:
    return {
        "schema": "withdrawal/v1",
        "withdraws": withdraws,
        "reason": "filed under the pre-v3.23 direction of the exhibit (F08-Q33)",
        "author": "founder",
        "date": "2026-10-04",
    }


def file_withdrawal(root: Path, withdraws: str = f"defects/{CLAIM_NAME}") -> str:
    return write_yaml(root, WITHDRAWAL, withdrawal_doc(withdraws))


def frontier_ids(root: Path) -> list[str]:
    prod = products.generate(root, rendered_from=RENDERED, commit_time=NOW)
    doc = json.loads(prod.files[Path("frontier.json")])
    return [str(e["node_id"]) for e in doc["entries"]]


# --- the record is a curator's, and the classifier knows it ---------------------------------------


def test_a_withdrawal_is_a_curator_record() -> None:
    """Today the path is no role at all, so the pull request is ``path-forbidden``."""
    located = paths.locate(WITHDRAWAL)
    assert located is not None and located.role == "withdrawal"
    classification = modes.classify(
        [Change("A", WITHDRAWAL)], author="founder-login", curators=CURATORS
    )
    assert classification.mode == "curator", classification.problems
    assert classification.reviewers == ("second-login",)  # F08-R8: another listed identity


def test_a_withdrawal_by_a_non_curator_is_refused() -> None:
    classification = modes.classify([Change("A", WITHDRAWAL)], author="mallory", curators=CURATORS)
    assert classification.mode is None
    assert [d.code for d in classification.problems] == ["curator-unlisted"]


def test_a_withdrawal_may_not_be_modified_or_deleted() -> None:
    for status in ("M", "D"):
        classification = modes.classify(
            [Change(status, WITHDRAWAL)],
            author="founder-login",
            curators=CURATORS,
        )
        assert classification.mode is None, status


def check_codes(root: Path, rel: str) -> list[str]:
    classification = modes.classify([Change("A", rel)], author="founder-login", curators=CURATORS)
    assert classification.mode == "curator", classification.problems
    return [d.code for d in modes.check(root, classification)]


def test_a_withdrawal_of_a_claim_on_the_record_passes_the_checks(tmp_path: Path) -> None:
    root = copy_graph(tmp_path)
    file_claim(root)
    assert schemas.violations(withdrawal_doc(), "withdrawal/v1") == []
    assert check_codes(root, file_withdrawal(root)) == []


def test_a_withdrawal_of_a_status_record_passes_the_checks(tmp_path: Path) -> None:
    root = copy_graph(tmp_path)
    file_status(root)
    assert check_codes(root, file_withdrawal(root, f"status/{STATUS_NAME}")) == []


def test_a_withdrawal_naming_a_file_that_does_not_exist_is_refused(tmp_path: Path) -> None:
    root = copy_graph(tmp_path)
    assert check_codes(root, file_withdrawal(root)) == ["withdrawal-unknown-record"]


def test_a_withdrawal_naming_a_record_on_another_node_is_refused(tmp_path: Path) -> None:
    """The record is named relative to the withdrawal's own node; the claim sits under the hole,
    so a withdrawal filed under the ancestor cannot reach it."""
    root = copy_graph(tmp_path)
    file_claim(root)
    rel = WITHDRAWAL.replace(f"/nodes/{HOLE}/", f"/nodes/{ANCESTOR}/")
    write_yaml(root, rel, withdrawal_doc())
    assert check_codes(root, rel) == ["withdrawal-unknown-record"]


def test_a_withdrawal_naming_a_file_on_another_target_is_refused(tmp_path: Path) -> None:
    """A path outside the node's own ``status/`` or ``defects/`` does not validate."""
    root = copy_graph(tmp_path)
    file_claim(root)
    other = f"targets/elsewhere/nodes/{HOLE}/defects/{CLAIM_NAME}"
    for named in (other, f"../../../elsewhere/nodes/{HOLE}/defects/{CLAIM_NAME}"):
        write_yaml(root, WITHDRAWAL, withdrawal_doc(named))
        assert check_codes(root, WITHDRAWAL) == ["record-invalid"], named


def test_a_withdrawal_of_a_withdrawal_is_refused(tmp_path: Path) -> None:
    root = copy_graph(tmp_path)
    write_yaml(root, WITHDRAWAL, withdrawal_doc("withdrawals/20261004T120000Z-founder.yaml"))
    assert check_codes(root, WITHDRAWAL) == ["record-invalid"]


# --- every reader reads a withdrawn record as absent ----------------------------------------------


def test_a_withdrawn_circularity_claim_puts_the_hole_back_on_the_frontier(tmp_path: Path) -> None:
    root = copy_graph(tmp_path, publish=True)
    file_claim(root)
    assert HOLE not in frontier_ids(root), "guard: the claim takes the hole off the frontier"
    file_withdrawal(root)
    assert HOLE in frontier_ids(root)
    node = graph.load_target(root, TARGET).nodes[HOLE]
    assert node.circular is None and node.circular_claims == ()
    assert (root / CLAIM).is_file(), "the withdrawn file stays in the tree"


def test_a_withdrawn_status_record_is_read_as_absent(tmp_path: Path) -> None:
    root = copy_graph(tmp_path)
    file_status(root, "abandoned")
    node_dir = root / NODE_DIR
    record = records.load_node_status(node_dir)
    assert record is not None and record.status == "abandoned", "guard"
    file_withdrawal(root, f"status/{STATUS_NAME}")
    assert records.load_node_status(node_dir) is None
    assert graph.load_target(root, TARGET).statuses[HOLE] == "ready"


def test_an_earlier_record_stands_once_the_latest_is_withdrawn(tmp_path: Path) -> None:
    """Absent means absent: the record before it is the latest again, whatever its date."""
    root = copy_graph(tmp_path)
    write_yaml(
        root,
        f"{NODE_DIR}/status/20260901T000000Z-founder.yaml",
        {
            "schema": "node-status/v1",
            "status": "abandoned",
            "cause": "the route is dead",
            "author": "founder",
            "date": "2026-09-01",
        },
    )
    file_status(root, "disputed")
    file_withdrawal(root, f"status/{STATUS_NAME}")
    record = records.load_node_status(root / NODE_DIR)
    assert record is not None and record.status == "abandoned"


def test_a_malformed_withdrawal_withdraws_nothing(tmp_path: Path) -> None:
    """A withdrawal that does not validate is passed over, so the record it names stands: one bad
    file must never decide what the graph says (2026-09-17)."""
    root = copy_graph(tmp_path)
    file_claim(root)
    write_yaml(root, WITHDRAWAL, {**withdrawal_doc(), "reason": ""})
    assert records.circular_claim(root / NODE_DIR) == f"defects/{CLAIM_NAME}"


def test_withdrawing_rewrites_nothing_and_a_revert_restores_the_products(tmp_path: Path) -> None:
    """Derive, never rewrite (F08-T10): removing the withdrawal (one commit's revert) restores
    the products byte for byte."""
    root = copy_graph(tmp_path, publish=True)
    file_claim(root)
    before = products.generate(root, rendered_from=RENDERED, commit_time=NOW).files
    claim_bytes = (root / CLAIM).read_bytes()
    file_withdrawal(root)
    products.generate(root, rendered_from=RENDERED, commit_time=NOW)
    assert (root / CLAIM).read_bytes() == claim_bytes
    (root / WITHDRAWAL).unlink()
    (root / WITHDRAWAL).parent.rmdir()
    assert products.generate(root, rendered_from=RENDERED, commit_time=NOW).files == before


# --- F08-T32 (D-18 v3.27): an exit from `disputed` -----------------------------------------------
#
# ``disputed`` is an adjudicator's record that rests on a claim (its ``reference``). Before v3.27 it
# had no exit but a later record, the trap ``stale`` had before v3.18. It lifts when its record, or
# the claim it rests on, is withdrawn, and the node's status is derived again from the tree — the
# shape of ``stale_is_void`` and ``speculative_is_void``. An upheld dispute ends in D-8's revision.


def test_a_disputed_record_stands_while_its_claim_does(tmp_path: Path) -> None:
    root = copy_graph(tmp_path)
    file_claim(root)
    file_status(root, "disputed", reference=f"defects/{CLAIM_NAME}")
    assert graph.load_target(root, TARGET).statuses[HOLE] == "disputed"


def test_a_disputed_record_lifts_when_the_claim_it_rests_on_is_withdrawn(tmp_path: Path) -> None:
    root = copy_graph(tmp_path)
    file_claim(root)
    file_status(root, "disputed", reference=f"defects/{CLAIM_NAME}")
    file_withdrawal(root)
    tg = graph.load_target(root, TARGET)
    assert tg.statuses[HOLE] == "ready"  # derived again from the tree
    assert (root / STATUS).is_file(), "the record stays; it is void, not removed"


def test_a_claim_named_by_its_full_graph_path_lifts_too(tmp_path: Path) -> None:
    root = copy_graph(tmp_path)
    file_claim(root)
    file_status(root, "disputed", reference=CLAIM)
    file_withdrawal(root)
    assert graph.load_target(root, TARGET).statuses[HOLE] == "ready"


def test_a_disputed_record_lifts_when_it_is_withdrawn_itself(tmp_path: Path) -> None:
    root = copy_graph(tmp_path)
    file_claim(root)
    file_status(root, "disputed", reference=f"defects/{CLAIM_NAME}")
    file_withdrawal(root, f"status/{STATUS_NAME}")
    assert graph.load_target(root, TARGET).statuses[HOLE] == "ready"


def test_withdrawing_another_claim_leaves_the_dispute_standing(tmp_path: Path) -> None:
    root = copy_graph(tmp_path)
    file_claim(root)
    other = CLAIM.replace("alice", "bob")
    (root / other).write_bytes((root / CLAIM).read_bytes())
    file_status(root, "disputed", reference=f"defects/{CLAIM_NAME}")
    file_withdrawal(root, f"defects/{other.rsplit('/', 1)[1]}")
    assert graph.load_target(root, TARGET).statuses[HOLE] == "disputed"


def test_a_withdrawn_claim_voids_only_a_disputed_record(tmp_path: Path) -> None:
    """An ``abandoned`` record is a curator's judgment on the route, not on a claim; naming the
    claim in its reference does not tie its fate to the claim's."""
    root = copy_graph(tmp_path)
    file_claim(root)
    file_status(root, "abandoned", reference=f"defects/{CLAIM_NAME}")
    file_withdrawal(root)
    assert graph.load_target(root, TARGET).statuses[HOLE] == "abandoned"
