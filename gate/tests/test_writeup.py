"""F15-T7 / AC8: write-up records (R6; D-32, D-33 v3.17).

A record that a paper or a state-of-the-problem note exists, signed by an active steward of the
target or a listed curator with their own key. It travels in the steward mode, alone or with
a commitment, and is refused by name when its signature fails or its signer is neither. A valid
``paper`` record is what makes a resolved target ``written-up`` (AC6, in ``test_products``).
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

from opn_gate import cli, modes, schemas, steward, writeup
from opn_gate.paths import Change
from opn_gate.signer import SshKeygenSigner
from opn_gate.writeup import WriteupError

TARGET = "euclid-primes"
STEWARD = "alice-steward"
PROVER = "bob-prover"
SIGNER = SshKeygenSigner()


@pytest.fixture(scope="module")
def keys(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Path]:
    d = tmp_path_factory.mktemp("writeup-keys")
    out: dict[str, Path] = {}
    for who in (CURATOR, STEWARD, PROVER):
        key = d / who
        subprocess.run(
            ["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(key), "-C", who],
            check=True,
        )
        out[who] = key
    return out


@pytest.fixture
def graph(tmp_path: Path, keys: dict[str, Path]) -> Path:
    root = copy_graph(tmp_path)
    take_in(root, TARGET)
    write_curators(root, CURATOR)
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
    return root


def record(root: Path, by: str, key: Path, *, kind: str = "paper", **overrides: Any) -> Change:
    path = writeup.write(
        root / "targets" / TARGET, kind=kind, title="On the problem", url="https://arxiv.org/abs/1",
        date="2026-09-16", signer_login=by, key_path=key, signer=SIGNER,
    )  # fmt: skip
    if overrides:
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        doc.update(overrides)
        path.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")
    return Change("A", path.relative_to(root).as_posix())


def codes(root: Path, *changes: Change, author: str = "anyone") -> list[str]:
    classification = modes.classify(list(changes), author=author)
    assert classification.mode == "steward", classification.as_dict()
    return [d.code for d in modes.check(root, classification)]


def test_a_stewards_record_is_accepted_and_a_provers_refused(
    graph: Path, keys: dict[str, Path]
) -> None:
    """AC8: signed by an active steward it is the steward mode and passes; by a listed curator
    too; by a prover it is refused naming the signer; a tampered one names the signature."""
    root = graph
    by_steward = record(root, STEWARD, keys[STEWARD])
    assert by_steward.path == f"targets/{TARGET}/writeup/1.yaml"
    c = modes.classify([by_steward], author="anyone")
    assert c.mode == "steward" and not c.needs_gate and not c.needs_review
    assert modes.check(root, c) == []
    assert [w.kind for w in writeup.valid(root / "targets" / TARGET, SIGNER)] == ["paper"]
    assert writeup.has_paper(root / "targets" / TARGET, SIGNER)

    by_curator = record(root, CURATOR, keys[CURATOR], kind="note")
    assert codes(root, by_curator) == []

    by_prover = record(root, PROVER, keys[PROVER])
    assert codes(root, by_prover) == ["writeup-signer"]
    (root / by_prover.path).unlink()

    tampered = record(root, STEWARD, keys[STEWARD], title="Retitled")
    assert codes(root, tampered) == ["writeup-signature"]
    (root / tampered.path).unlink()

    elsewhere = record(root, STEWARD, keys[STEWARD], target="other-target")
    assert codes(root, elsewhere) == ["writeup-target"]
    (root / elsewhere.path).unlink()

    # A commitment and a write-up in one pull request: the steward is active by its own record.
    steward.write(
        root / "targets" / TARGET, action=steward.STEP_DOWN, login=STEWARD, date="2026-09-17",
        key_path=keys[STEWARD], signer=SIGNER,
    )  # fmt: skip
    gone = record(root, STEWARD, keys[STEWARD])
    assert codes(root, gone) == ["writeup-signer"]
    (root / gone.path).unlink()
    again = steward.write(
        root / "targets" / TARGET, action=steward.COMMIT, login=STEWARD, name="Alice",
        link="https://orcid.org/0000-0002-1825-0097", date="2026-09-18",
        key_path=keys[STEWARD], signer=SIGNER,
    )  # fmt: skip
    both = [Change("A", again.relative_to(root).as_posix()), record(root, STEWARD, keys[STEWARD])]
    assert codes(root, *both) == []

    # Append-only, numbered, and never an append's or a proof's companion.
    assert modes.classify([Change("M", by_steward.path)]).problems[0].code == "path-forbidden"
    proof = Change("A", f"targets/{TARGET}/nodes/and-reassoc/Proof.lean")
    assert [d.code for d in modes.classify([by_steward, proof]).problems] == ["mode-mixed"]
    with pytest.raises(WriteupError, match="https"):
        writeup.write(
            root / "targets" / TARGET, kind="paper", title="t", url="http://x", date="2026-09-16",
            signer_login=STEWARD, key_path=keys[STEWARD], signer=SIGNER,
        )  # fmt: skip
    with pytest.raises(WriteupError, match="paper or a note"):
        writeup.write(
            root / "targets" / TARGET, kind="blog", title="t", url="https://x", date="2026-09-16",
            signer_login=STEWARD, key_path=keys[STEWARD], signer=SIGNER,
        )  # fmt: skip


def test_writeup_record_command(
    graph: Path, keys: dict[str, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    """R6: ``opn-gate writeup record`` writes one signed record; a refusal is exit 1."""
    argv = [
        "writeup", "record", TARGET, "--graph", str(graph), "--kind", "paper",
        "--title", "Digested", "--url", "https://arxiv.org/abs/2609.00001", "--by", STEWARD,
        "--key", str(keys[STEWARD]), "--date", "2026-09-16T00:00:00Z",
    ]  # fmt: skip
    code = cli.main(argv)
    out = json.loads(capsys.readouterr().out)
    assert code == cli.EXIT_PASS, out
    assert out["written"] == [f"targets/{TARGET}/writeup/1.yaml"]
    doc = schemas.load_yaml(graph / out["written"][0], "writeup/v1")
    assert doc["kind"] == "paper" and doc["signer"] == STEWARD
    argv[argv.index("--url") + 1] = "http://insecure"
    code = cli.main(argv)
    out = json.loads(capsys.readouterr().out)
    assert code == cli.EXIT_FAIL and out["ok"] is False
