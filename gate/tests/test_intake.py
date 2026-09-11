"""F11: the selection record (T1; R7; AC8) and curated intake (T2; R2, R4, R5; AC1-AC3, AC5).

Two halves. The selection record is prose the curator writes, so what a test can hold is its
*completeness*: that it names the chosen result, answers each of R7's six criteria with evidence,
and rejects two alternatives with reasons — the parts a reader needs and a hurried session drops.

The intake half is all refusals, which is what D-6 is: a target is listed only once five
artifacts exist, and the tooling's job is to say which one is missing rather than to decide. Every
refusal is checked to leave the graph untouched (C7), because a half-written target is worse than
no target.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest
import samples
import yaml
from harness import TARGET, copy_graph, take_in

from opn_gate import fidelity, intake, products, schemas
from opn_gate.intake import IntakeError

REPO = Path(__file__).resolve().parents[2]
SELECTION = REPO / "engineering" / "evidence" / "F11" / "selection.md"
ANNEX = Path(__file__).resolve().parent / "fixtures" / "onramp" / "annex.md"

#: R7's criteria, each as the slug of its `###` heading under `## Criteria`. One heading per
#: criterion, so a criterion that was never answered is a missing key rather than a thin
#: paragraph nobody notices.
R7_CRITERIA: tuple[str, ...] = (
    "elementary-in-an-included-domain",
    "objects-defined-in-the-graphs-own-defs",
    "statable-in-under-40-lines",
    "at-most-three-definitions",
    "decomposable-into-three-to-six-lemmas",
    "mathlib-still-pinned",
)
MIN_REJECTED = 2  # R7: "two rejected alternatives and why"
MIN_LEMMAS, MAX_LEMMAS = 3, 6  # R7's band, counted as rows of the lemma-structure table


def sections(text: str, level: int) -> dict[str, str]:
    """Headings of exactly ``level`` hashes, mapped to the body under each."""
    pattern = re.compile(rf"^{'#' * level} +(?P<title>.+?)\s*$", re.M)
    found = list(pattern.finditer(text))
    out: dict[str, str] = {}
    for i, m in enumerate(found):
        end = found[i + 1].start() if i + 1 < len(found) else len(text)
        out[m.group("title").strip()] = text[m.end() : end]
    return out


def subsections(body: str) -> dict[str, str]:
    return sections(body, 3)


@pytest.fixture(scope="module")
def record() -> str:
    assert SELECTION.is_file(), f"the selection record R7 requires is missing: {SELECTION}"
    return SELECTION.read_text(encoding="utf-8")


def test_selection_record_complete(record: str) -> None:
    """AC8: the record names the chosen result, each R7 criterion with evidence, and two
    rejected alternatives."""
    top = sections(record, 2)
    wanted = ("Chosen", "Definitions", "Lemma structure", "Criteria", "Rejected alternatives")
    for heading in wanted:
        assert heading in top, f"the selection record has no '## {heading}' section"

    chosen = top["Chosen"]
    assert re.search(r"^-\s+\*\*theorem:\*\*\s+\S", chosen, re.M), "no chosen theorem is named"
    assert re.search(r"^-\s+\*\*root statement:\*\*\s+\S", chosen, re.M), "no root statement"

    criteria = subsections(top["Criteria"])
    missing = [c for c in R7_CRITERIA if c not in criteria]
    assert not missing, f"R7 criteria with no heading in the record: {', '.join(missing)}"
    unanswered = [c for c in R7_CRITERIA if not re.search(r"^evidence:\s*\S", criteria[c], re.M)]
    assert not unanswered, f"R7 criteria with a heading but no evidence: {', '.join(unanswered)}"

    rejected = subsections(top["Rejected alternatives"])
    assert len(rejected) >= MIN_REJECTED, (
        f"R7 wants two rejected alternatives; the record has {len(rejected)}"
    )
    silent = [name for name, body in rejected.items() if not re.search(r"why rejected:", body)]
    assert not silent, f"rejected alternatives with no reason: {', '.join(silent)}"


def test_selection_lemma_structure_is_in_r7s_band(record: str) -> None:
    """AC8, R7: three to six lemmas. Counted from the record rather than asserted in prose, so a
    later edit to the table cannot quietly leave the band."""
    table = sections(record, 2)["Lemma structure"]
    rows = [
        line
        for line in table.splitlines()
        if line.strip().startswith("|") and not re.match(r"^\s*\|[\s|:-]+\|\s*$", line)
    ]
    nodes = len(rows) - 1  # the header row
    assert MIN_LEMMAS <= nodes <= MAX_LEMMAS, (
        f"R7 asks for three to six lemmas; the record's table has {nodes} nodes"
    )
    assert re.search(r"\(root\)", table), "the lemma table does not mark which node is the root"


def test_selection_names_the_annex_the_skeleton_will_cite(record: str) -> None:
    """R8: the skeleton submitted in T4 cites an annex holding the paper's argument, so T1 has
    to leave one behind and the record has to say where it is (D-31)."""
    assert ANNEX.is_file(), f"the annex text R8's skeleton cites is missing: {ANNEX}"
    rel = ANNEX.relative_to(REPO).as_posix()
    assert rel in record, f"the selection record does not point at the annex at {rel}"
    text = ANNEX.read_text(encoding="utf-8")
    assert "D-31" in text, "the annex does not say what it is (untrusted input, D-31)"


# --- T2: curated intake (R2, R4, R5; AC1, AC2, AC3, AC5) ---------------------------------------

DEFS = {"Primes.lean": "def Opn.IsPrime (p : Nat) : Prop := 2 ≤ p\n"}
LATER = "2026-09-12T00:00:00Z"


def generate(root: Path) -> dict[str, Any]:
    """The products, as documents keyed by path."""
    prod = products.generate(root, rendered_from="5" * 40, commit_time="2026-09-11T00:00:00Z")
    return {p.as_posix(): json.loads(data) for p, data in prod.files.items()}


def index_row(root: Path, target_id: str) -> dict[str, Any]:
    rows = generate(root)["targets/index.json"]["targets"]
    return next(r for r in rows if r["target_id"] == target_id)


def test_five_artifacts_required(tmp_path: Path) -> None:
    """AC1: a record with no prior art is refused naming it; with every artifact present and no
    attack routes, intake proceeds (R2: attack routes may be empty)."""
    root = copy_graph(tmp_path)
    with pytest.raises(IntakeError) as refusal:
        take_in(root, prior_art={"arxiv_query": None, "forum_url": None, "summary": "   "})
    assert "prior art" in str(refusal.value) and "D-6" in str(refusal.value)
    assert not (root / "targets" / "euclid-primes").exists(), "a refusal left a target behind"

    result = take_in(root, attack_routes=[])
    assert result.target_id == "euclid-primes"
    assert (root / "targets" / "euclid-primes" / intake.TARGET_FILE).is_file()


def test_a_target_with_no_root_witness_is_refused(tmp_path: Path) -> None:
    """R2's fifth artifact. The witness slot exists on every node (D-3), so the check that
    matters is that it has been *filled* — an empty one is the absence D-6 is asking about."""
    root = copy_graph(tmp_path)
    witness = root / "targets" / TARGET / "nodes" / "and-reassoc" / "Witness.lean"
    witness.write_text("-- TODO\nexample : True := sorry\n", encoding="utf-8")
    with pytest.raises(IntakeError, match="witness"):
        take_in(root)
    assert not (root / "targets" / "euclid-primes").exists()


def test_excluded_domains(tmp_path: Path) -> None:
    """AC2: a target tagged `pde` is refused citing D-6, and nothing is written."""
    root = copy_graph(tmp_path)
    with pytest.raises(IntakeError) as refusal:
        take_in(root, domains=["number-theory", "pde"])
    assert "pde" in str(refusal.value) and "D-6" in str(refusal.value)
    assert not (root / "targets" / "euclid-primes").exists()


def test_an_unlicensed_source_may_not_have_its_statement_reproduced(tmp_path: Path) -> None:
    """R10, enforced at the record: erdosproblems.com states no licence, so its wording is not
    stored at all and the network's paraphrase stands in its place."""
    root = copy_graph(tmp_path)
    source = {
        "kind": "erdos",
        "url": "https://www.erdosproblems.com/1",
        "accessed": "2026-09-11",
        "licence": "none-stated",
        "attribution": "erdosproblems.com",
        "quote_policy": "cite",
    }
    with pytest.raises(IntakeError, match="may not be reproduced"):
        take_in(root, sources=[source])
    with pytest.raises(IntakeError, match="paraphrase"):
        take_in(root, sources=[source], informal=None)
    result = take_in(root, sources=[source], informal=None, paraphrase="A question about primes.")
    assert result.target_id == "euclid-primes"


def test_scaffold_state(tmp_path: Path) -> None:
    """AC3: the spec pins the given SHA, every certificate is mechanical-only, the status is
    listed, and the target is not claimable."""
    root = copy_graph(tmp_path)
    take_in(root, defs=DEFS)
    target = root / "targets" / "euclid-primes"

    spec = schemas.load_json(target / "gate-spec.json", "gate-spec/v1")
    assert spec["mathlib_sha"] == "a" * 40 and spec["graph_id"] == "euclid-primes"
    # The gate's own settings are inherited from the graph, never invented (R2).
    assert spec["axiom_allowlist"] == ["propext", "Classical.choice", "Quot.sound"]

    rows = {row.subject: row for row in fidelity.subject_grades(target)}
    assert sorted(rows) == ["Primes", "root"]
    assert all(row.grade == "mechanical-only" for row in rows.values())
    assert all(row.signers == () for row in rows.values()), "the machine's grade signs for nobody"

    row = index_row(root, "euclid-primes")
    assert row["status"] == "listed" and row["claimable"] is False
    assert row["fidelity"] == "mechanical-only" and row["track"] == "formalization"
    assert set(row["not_claimable"]) == {
        "status-listed",
        "grade-below-screened-and-signed",
        "no-posting",
    }
    entries = [
        e for e in generate(root)["frontier.json"]["entries"] if e["target_id"] == "euclid-primes"
    ]
    assert entries and all(e["claimable"] is False for e in entries)
    assert all(e["dormant"] is False for e in entries)


def test_activation_requires_posting(tmp_path: Path) -> None:
    """AC5: screened-and-signed with no posting is refused naming the posting; with one, the
    target is active and its nodes are claimable."""
    root = copy_graph(tmp_path)
    take_in(root)
    target = root / "targets" / "euclid-primes"
    fidelity.attest(
        target,
        "root",
        "screened-and-signed",
        attestor="reviewer",
        date="2026-09-11",
        evidence="read the Lean against the English",
    )
    with pytest.raises(IntakeError) as refusal:
        intake.activate(root, "euclid-primes", author="curator", date=LATER)
    assert "posted upstream" in str(refusal.value) and "D-10" in str(refusal.value)

    intake.post(
        root,
        "euclid-primes",
        venue="erdosproblems.com",
        url="https://example.org/posting",
        date=LATER,
    )
    intake.activate(root, "euclid-primes", author="curator", date=LATER)
    row = index_row(root, "euclid-primes")
    assert row["status"] == "active" and row["claimable"] is True
    assert row["not_claimable"] == [] and row["posting"]["venue"] == "erdosproblems.com"
    assert row["fidelity"] == "screened-and-signed"


def test_a_posting_is_recorded_once(tmp_path: Path) -> None:
    """R5: a posting is a fact about the world, so a second one is a refusal, not a rewrite."""
    root = copy_graph(tmp_path)
    take_in(root)
    intake.post(root, "euclid-primes", venue="v", url="https://example.org/a", date=LATER)
    with pytest.raises(IntakeError, match="already posted"):
        intake.post(root, "euclid-primes", venue="v", url="https://example.org/b", date=LATER)
    doc = intake.load_doc(root / "targets" / "euclid-primes")
    assert doc is not None and doc["posting"]["url"] == "https://example.org/a"


def test_admission_refusal_leaves_no_target(tmp_path: Path) -> None:
    """R2, C7: admission runs on the scaffolded tree, so a failure has to unwind it whole."""
    root = copy_graph(tmp_path)

    def refuse(path: Path, subject: str) -> intake.SubjectCheck:
        return intake.SubjectCheck(subject, subject != "root", "does not elaborate")

    with pytest.raises(IntakeError, match="admission refused"):
        take_in(root, checker=refuse)
    assert not (root / "targets" / "euclid-primes").exists()
    assert sorted(p.name for p in (root / "targets").iterdir()) == [TARGET]


def test_intake_never_touches_an_existing_target(tmp_path: Path) -> None:
    """D-3: a target's directory is not something a second intake may write into."""
    root = copy_graph(tmp_path)
    before = (root / "targets" / TARGET / "gate-spec.json").read_bytes()
    with pytest.raises(IntakeError, match="already exists"):
        take_in(root, target_id=TARGET)
    assert (root / "targets" / TARGET / "gate-spec.json").read_bytes() == before


def test_a_pre_f11_target_keeps_f03s_rule(tmp_path: Path) -> None:
    """R4 applies to curated targets. The tutorial graph has no target.yaml and its declaration
    still speaks for it (F03-Q4, Q5) — the one thing the rung rename must not break."""
    root = copy_graph(tmp_path)
    status = root / "targets" / TARGET / "status"
    status.mkdir()
    (status / "2026-09-09-1.yaml").write_text(
        yaml.safe_dump(samples.target_status(claimable=True)), encoding="utf-8"
    )
    row = index_row(root, TARGET)
    assert row["claimable"] is True and row["not_claimable"] == []
    assert row["track"] is None and row["subjects"] == []
