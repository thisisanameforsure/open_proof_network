"""F07-T38: an alternate's post-merge job records why step 9 was not asked (testers 2026-09-23).

D-4 v3.13 asks no review of an alternate, and the classifier said so by answering no review kind
at all. The post-merge job passes that answer as ``--review-kind``, which is required and takes one
of six words, so every merged alternate's job died at argument parsing: #162, #163, #164, #167 and
#172 (the erdos-69 racers F07-T36 moved to their alternate paths) merged with no attestation and
no bot commit. The first live alternates were the first to reach that path. An alternate settles
nothing — its node is already proved — so it carries the reason v3.20 gave for exactly that:
``calibration`` on a calibration target, ``intermediate`` elsewhere.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import samples
import yaml
from test_finding_step9_certified import ROOT, Repo, classify, curated, step9
from test_finding_step9_root_only import NOT_ASKED_CALIBRATION, NOT_ASKED_INTERMEDIATE

from opn_gate import postmerge, schemas

ALTERNATE = "attempts/20260923T145210Z-someone-alternate.lean"


def proved_root(tmp_path: Path, *, calibration: bool) -> tuple[Repo, str]:
    repo, _proof = curated(tmp_path, keep_proof=True)
    doc = samples.attestation(
        node_id=ROOT,
        statement_hash=schemas.content_hash((repo.node / "Statement.lean").read_bytes()),
        merge_commit="2" * 40,
        graph_commit="1" * 40,
        runner="hosted",
    )
    (repo.root / "attestations").mkdir(exist_ok=True)
    (repo.root / "attestations" / "000001.json").write_bytes(schemas.canonical_json(doc))
    if calibration:
        record = repo.target / "target.yaml"
        target: dict[str, Any] = yaml.safe_load(record.read_text(encoding="utf-8"))
        target["calibration"] = True
        record.write_text(yaml.safe_dump(target, sort_keys=False), encoding="utf-8")
    repo.commit("base: the root, proved")
    text = (repo.node / "Proof.lean").read_text(encoding="utf-8")
    return repo, text.replace("theorem", "-- another road\ntheorem", 1) + "\n-- different\n"


@pytest.mark.parametrize(
    ("calibration", "expected"),
    [(False, NOT_ASKED_INTERMEDIATE), (True, NOT_ASKED_CALIBRATION)],
)
def test_an_alternate_says_why_nobody_was_asked(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], calibration: bool, expected: Any
) -> None:
    repo, text = proved_root(tmp_path, calibration=calibration)
    path = repo.node / ALTERNATE
    path.parent.mkdir(exist_ok=True)
    path.write_text(text, encoding="utf-8")
    repo.commit("an alternate proof")
    code, out = classify(repo, capsys)
    assert code == 0 and out["mode"] == "alternate", out
    assert step9(out) == expected, out
    # and the post-merge command takes it: the kind is one of the six it accepts
    review = postmerge.review_block(out["review_kind"])
    assert review["kind"] == expected[1] and review["reviewer"] is None
