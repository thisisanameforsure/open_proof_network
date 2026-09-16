"""F15-T6 / AC7: signed explainers (R8; D-3 v3.17, D-33 v3.17).

A signature on an explainer is a comprehension claim by a real-identity contributor — at Stage 0
an active steward of the target or a listed curator (F15-Q4) — affirming one fixed sentence. It
merges in the explainer mode on the path and signature checks alone, claims nothing about the
mathematics, and earns nothing; only its validity matters, and each way it can be invalid is
refused by name before it merges. Every signature here is a real ``ssh-keygen`` one.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml
from harness import copy_graph, take_in
from test_modes import CURATOR, write_curators

from opn_gate import cli, explainers, ledger, modes, schemas, signed, steward
from opn_gate.explainers import ExplainerError
from opn_gate.paths import Change
from opn_gate.signer import SshKeygenSigner

TARGET = "euclid-primes"
NODE = "and-reassoc"  # take_in's root, which carries the fixture's proof
STEWARD = "alice-steward"
SIGNER = SshKeygenSigner()
EXPLAINER = (
    "---\nauthor: someone\nmodel: claude-fable-5-1\ndate: 2026-09-16\n---\n"
    "Reassociate the conjunction: both halves are already in hand.\n"
)


@pytest.fixture(scope="module")
def keys(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Path]:
    d = tmp_path_factory.mktemp("explainer-keys")
    out: dict[str, Path] = {}
    for who in (CURATOR, STEWARD, "stranger"):
        key = d / who
        subprocess.run(
            ["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(key), "-C", who],
            check=True,
        )
        out[who] = key
    return out


@pytest.fixture
def graph(tmp_path: Path, keys: dict[str, Path]) -> tuple[Path, Path, str]:
    """A curated target whose root is proved and carries one explainer; the curator listed;
    a steward committed. Returns (graph root, node dir, explainer hash)."""
    root = copy_graph(tmp_path)
    take_in(root, TARGET)
    write_curators(root, CURATOR)
    node = root / "targets" / TARGET / "nodes" / NODE
    assert (node / "Proof.lean").is_file()
    digest = schemas.content_hash(EXPLAINER.encode("utf-8"))
    (node / "explainer").mkdir(exist_ok=True)
    (node / "explainer" / f"{digest}.md").write_text(EXPLAINER, encoding="utf-8")
    steward.write(
        root / "targets" / TARGET,
        action=steward.COMMIT,
        login=STEWARD,
        name="Alice",
        link="https://orcid.org/0000-0002-1825-0097",
        date="2026-09-16",
        key_path=keys[STEWARD],
        signer=SIGNER,
    )
    return root, node, digest


def sign(node_dir: Path, digest: str, by: str, key: Path, **overrides: Any) -> Change:
    """A signature file as a pull request would add it; ``overrides`` are applied after signing,
    so a tampered field is what the gate must refuse."""
    path = explainers.sign(
        node_dir, digest, target_id=TARGET, signer_login=by, date="2026-09-16", key_path=key,
        signer=SIGNER,
    )  # fmt: skip
    if overrides:
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        doc.update(overrides)
        path.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")
    return Change("A", path.relative_to(node_dir.parents[3]).as_posix())


def codes(root: Path, *changes: Change) -> list[str]:
    classification = modes.classify(list(changes), author="anyone")
    assert classification.mode == "explainer", classification.as_dict()
    return [d.code for d in modes.check(root, classification)]


def test_a_curator_signs_and_the_pull_request_merges_on_the_path_check(
    graph: tuple[Path, Path, str], keys: dict[str, Path]
) -> None:
    """AC7: a curator's signature on a proved node's explainer is the explainer mode, needs no
    build, no admission and no review, and passes every check; a steward's does too; a
    signature arriving with the explainer it signs is accepted in one pull request."""
    root, node, digest = graph
    change = sign(node, digest, CURATOR, keys[CURATOR])
    assert change.path.endswith(f"/explainer/signed/{digest}-1.yaml")
    classification = modes.classify([change], author="anyone")
    assert classification.mode == "explainer" and classification.node_id == NODE
    assert not classification.needs_gate and not classification.needs_review
    assert not classification.needs_admission
    assert modes.check(root, classification) == []
    assert ledger.MERGE_LINES["explainer"] is None  # earns nothing at merge (R8)
    [valid] = explainers.valid(node, SIGNER)
    assert valid.signer == CURATOR and valid.explainer == digest

    by_steward = sign(node, digest, STEWARD, keys[STEWARD])
    assert by_steward.path.endswith("-2.yaml")
    assert codes(root, by_steward) == []

    # Explainer and signature together.
    second = "---\nauthor: other\ndate: 2026-09-16\n---\nAnother account.\n"
    other = schemas.content_hash(second.encode("utf-8"))
    (node / "explainer" / f"{other}.md").write_text(second, encoding="utf-8")
    explainer_change = Change("A", f"targets/{TARGET}/nodes/{NODE}/explainer/{other}.md")
    assert codes(root, explainer_change, sign(node, other, CURATOR, keys[CURATOR])) == []


def test_each_defect_is_refused_by_name(
    graph: tuple[Path, Path, str], keys: dict[str, Path]
) -> None:
    """AC7: an absent explainer, an altered sentence, a failed signature and a signer who is
    neither steward nor curator are each named; a file under another node is named too."""
    root, node, digest = graph
    # Absent: the command refuses before writing; a file smuggled in by hand is refused at the
    # gate — and it is named for the explainer it claims, so a misnamed one is caught as well.
    with pytest.raises(ExplainerError, match="nothing to sign"):
        explainers.sign(
            node, "f" * 64, target_id=TARGET, signer_login=CURATOR, date="2026-09-16",
            key_path=keys[CURATOR], signer=SIGNER,
        )  # fmt: skip
    assert not explainers.signed_dir(node).exists()
    absent = sign(node, digest, CURATOR, keys[CURATOR], explainer="f" * 64)
    assert codes(root, absent) == ["explainer-absent", "signature-invalid", "signature-name"]
    (root / absent.path).unlink()

    altered = sign(node, digest, CURATOR, keys[CURATOR], affirmation="I skimmed it.")
    assert codes(root, altered) == ["affirmation-differs", "signature-invalid"]
    (root / altered.path).unlink()

    tampered = sign(node, digest, CURATOR, keys[CURATOR], date="2026-09-17")
    assert codes(root, tampered) == ["signature-invalid"]
    (root / tampered.path).unlink()

    stranger = sign(node, digest, "stranger", keys["stranger"])
    assert codes(root, stranger) == ["signer-unlisted"]
    (root / stranger.path).unlink()

    # A steward who stepped down is no longer real-identity for this target.
    steward.write(
        root / "targets" / TARGET, action=steward.STEP_DOWN, login=STEWARD, date="2026-09-17",
        key_path=keys[STEWARD], signer=SIGNER,
    )  # fmt: skip
    gone = sign(node, digest, STEWARD, keys[STEWARD])
    assert codes(root, gone) == ["signer-unlisted"]
    (root / gone.path).unlink()

    # A signature that names another node than the one it sits under.
    misplaced = sign(node, digest, CURATOR, keys[CURATOR], node="other-node")
    assert codes(root, misplaced) == ["signature-node"]
    (root / misplaced.path).unlink()

    # Path grammar: a signature is a flat yaml under explainer/signed/, added once.
    prefix = f"targets/{TARGET}/nodes/{NODE}/explainer/signed"
    assert modes.classify([Change("A", f"{prefix}/notes.txt")]).problems[0].code == "path-forbidden"
    assert modes.classify([Change("M", f"{prefix}/{digest}-1.yaml")]).problems[0].code == (
        "path-forbidden"
    )
    mixed = modes.classify(
        [
            Change("A", f"{prefix}/{digest}-1.yaml"),
            Change("A", f"targets/{TARGET}/nodes/{NODE}/Proof.lean"),
        ]
    )
    assert [d.code for d in mixed.problems] == ["mode-mixed"]


def test_only_valid_signatures_count(graph: tuple[Path, Path, str], keys: dict[str, Path]) -> None:
    """R7's input: ``explainers.valid`` keeps the signatures that verify on a present explainer
    with the fixed sentence, and names why the others do not."""
    _root, node, digest = graph
    sign(node, digest, CURATOR, keys[CURATOR])
    sign(node, digest, CURATOR, keys[CURATOR], date="2026-09-01")  # tampered after signing
    loaded = explainers.load(node)
    assert [s.n for s in loaded] == [1, 2]
    assert [s.signer for s in explainers.valid(node, SIGNER)] == [CURATOR]
    assert explainers.problems_of(loaded[1], node, SIGNER) == (
        "signature-invalid: the signature does not verify under the record's key",
    )
    assert signed.verifies(loaded[0].doc, SIGNER)
    # A file under signed/ that is not a signature is a graph defect, not a skipped file.
    (explainers.signed_dir(node) / "notes.yaml").write_text("x: 1\n", encoding="utf-8")
    with pytest.raises(schemas.SchemaError):
        explainers.load(node)


def test_explainer_sign_command(
    graph: tuple[Path, Path, str], keys: dict[str, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    """R8: ``opn-gate explainer sign`` writes one signature with the signer's own key, and
    refuses with exit 1 and nothing written when the explainer is not on the node."""
    root, node, digest = graph
    argv = [
        "explainer", "sign", TARGET, NODE, digest, "--graph", str(root), "--by", CURATOR,
        "--key", str(keys[CURATOR]), "--date", "2026-09-16T00:00:00Z",
    ]  # fmt: skip
    code = cli.main(argv)
    out = json.loads(capsys.readouterr().out)
    assert code == cli.EXIT_PASS, out
    assert out["written"] == [f"targets/{TARGET}/nodes/{NODE}/explainer/signed/{digest}-1.yaml"]
    doc = schemas.load_yaml(root / out["written"][0], "explainer-signature/v1")
    assert doc["affirmation"] == explainers.AFFIRMATION and doc["signer"] == CURATOR

    argv[4] = "e" * 64
    code = cli.main(argv)
    out = json.loads(capsys.readouterr().out)
    assert code == cli.EXIT_FAIL and out["ok"] is False and "nothing to sign" in out["refused"]
    assert sorted(p.name for p in explainers.signed_dir(node).iterdir()) == [f"{digest}-1.yaml"]
