"""F20-T7 / AC10: the steward's commands (R12).

``opn-gate gloss revise <target> <subject>`` writes the current version of a gloss or explainer to
an editable file with ``supersedes`` and ``lean_hash`` (or ``proof``) filled in;
``opn-gate gloss file <path>`` checks R1 to R6 on the edited copy, names it by its hash and places
it; ``opn-gate gloss sign`` writes a gloss signature as ``explainer sign`` writes an explainer's.
Every refusal is ``{"ok": false, ...}`` and exit 1 with nothing left behind; a bad invocation is
exit 2 on stderr, never a traceback.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml
from harness import TARGET, copy_graph
from test_modes import CURATOR, write_curators

from opn_gate import cli, glosses, modes, schemas, signed
from opn_gate.paths import Change

NODE = "and-reassoc"


@pytest.fixture(scope="module")
def key(tmp_path_factory: pytest.TempPathFactory) -> Path:
    path = tmp_path_factory.mktemp("gloss-cli-key") / "curator"
    subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(path)], check=True)
    return path


@pytest.fixture
def root(tmp_path: Path) -> Path:
    graph = copy_graph(tmp_path)
    write_curators(graph, CURATOR)
    return graph


def node_dir(root: Path) -> Path:
    return root / "targets" / TARGET / "nodes" / NODE


def run(capsys: pytest.CaptureFixture[str], *argv: str) -> tuple[int, dict[str, Any]]:
    code = cli.main(list(argv))
    out = capsys.readouterr().out
    return code, json.loads(out) if out.strip() else {}


def seed_gloss(root: Path, body: str = "The statement reassociates a conjunction.\n") -> str:
    file = node_dir(root) / "Statement.lean"
    doc = {
        "schema": "gloss/v1",
        "target": TARGET,
        "subject": {
            "kind": "statement",
            "node": NODE,
            "module": None,
            "lean_hash": schemas.content_hash(file.read_bytes()),
        },
        "supersedes": None,
        "author": None,
        "drafter": {
            "name": "opn-drafter",
            "model": "a-model",
            "model_version": "1",
            "input_commit": "a" * 40,
        },
        "date": "2026-10-04",
        "licence": "CC-BY-4.0",
    }
    text = "---\n" + str(yaml.safe_dump(doc, sort_keys=False)) + "---\n" + body
    digest = schemas.content_hash(text.encode("utf-8"))
    (node_dir(root) / "gloss").mkdir(exist_ok=True)
    (node_dir(root) / "gloss" / f"{digest}.md").write_text(text, encoding="utf-8")
    return digest


def classified(root: Path, rel: str, author: str = "steward-login") -> list[str]:
    classification = modes.classify(
        [Change("A", rel)], author=author, curators=modes.load_curators(root), graph_root=root
    )
    assert classification.mode == "explainer", classification.as_dict()
    return [d.code for d in modes.check(root, classification)]


def test_revise_then_file_supersedes_the_head(
    root: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """AC10: revise writes the head's text with supersedes and the current lean_hash filled in;
    an edited copy, filed, is named by its hash under gloss/, supersedes the head, and the gate's
    classifier passes it. The head is a merged draft (``seed_gloss``): restated by F21-R2, a
    draft on the record stays supersedable by a person, while a new one is refused
    (``test_file_refuses_a_new_draft``)."""
    head = seed_gloss(root)
    draft = tmp_path / "edit.md"
    code, out = run(
        capsys, "gloss", "revise", TARGET, f"statement:{NODE}", "--graph", str(root),
        "--by", "carol", "--out", str(draft), "--date", "2026-10-05T00:00:00Z",
    )  # fmt: skip
    assert code == 0 and out["ok"] is True and out["supersedes"] == head
    doc, body = glosses.split_front_matter(draft.read_text(encoding="utf-8"))
    assert doc is not None
    assert doc["supersedes"] == head and doc["author"] == "carol" and doc["drafter"] is None
    # F21-R6: revise writes the record version the service writes, v2, with drafted_with open
    # for the person to fill in if a model helped (null: their own words)
    assert doc["schema"] == "gloss/v2" and "drafted_with" in doc and doc["drafted_with"] is None
    lean = schemas.content_hash((node_dir(root) / "Statement.lean").read_bytes())
    assert doc["subject"]["lean_hash"] == lean and doc["date"] == "2026-10-05"
    assert "reassociates" in body  # the head's words, to correct rather than retype
    draft.write_text(draft.read_text(encoding="utf-8") + "Corrected by hand.\n", encoding="utf-8")

    code, out = run(capsys, "gloss", "file", str(draft), "--graph", str(root))
    assert code == 0 and out["ok"] is True, out
    [written] = out["written"]
    path = root / written
    assert written.startswith(f"targets/{TARGET}/nodes/{NODE}/gloss/")
    assert path.stem == schemas.content_hash(path.read_bytes())
    assert classified(root, written) == []
    # Filed twice is refused, and nothing new is written.
    before = sorted((node_dir(root) / "gloss").iterdir())
    code, out = run(capsys, "gloss", "file", str(draft), "--graph", str(root))
    assert code == 1 and out["ok"] is False
    assert sorted((node_dir(root) / "gloss").iterdir()) == before


def test_file_refuses_a_new_draft(
    root: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """F21-R2 (restating F20-T10's draft case): a revised copy that keeps a drafter block in
    place of its author is a new draft, refused ``draft-not-accepted`` with nothing written."""
    seed_gloss(root)
    edit = tmp_path / "edit.md"
    run(capsys, "gloss", "revise", TARGET, f"statement:{NODE}", "--graph", str(root),
        "--by", "carol", "--out", str(edit))  # fmt: skip
    doc, body = glosses.split_front_matter(edit.read_text(encoding="utf-8"))
    assert doc is not None
    doc |= {"author": None, "drafter": {"name": "opn-drafter", "model": "m",
            "model_version": "1", "input_commit": "b" * 40}}  # fmt: skip
    edit.write_text("---\n" + yaml.safe_dump(doc, sort_keys=False) + "---\n" + body, "utf-8")
    before = sorted((node_dir(root) / "gloss").iterdir())
    code, out = run(capsys, "gloss", "file", str(edit), "--graph", str(root))
    assert code == 1 and out["ok"] is False
    assert [p["code"] for p in out["problems"]] == ["draft-not-accepted"]
    assert sorted((node_dir(root) / "gloss").iterdir()) == before


def test_file_refuses_what_the_gate_refuses_and_leaves_nothing(
    root: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """R12: file runs R1 to R6 and refuses with the gate's code, writing nothing: here a stale
    lean_hash, and a version superseding a non-head."""
    head = seed_gloss(root)
    draft = tmp_path / "edit.md"
    run(capsys, "gloss", "revise", TARGET, f"statement:{NODE}", "--graph", str(root),
        "--by", "carol", "--out", str(draft))  # fmt: skip
    text = draft.read_text(encoding="utf-8")
    stale = tmp_path / "stale.md"
    lean = schemas.content_hash((node_dir(root) / "Statement.lean").read_bytes())
    stale.write_text(text.replace(lean, "a" * 64), encoding="utf-8")  # still a string in YAML
    before = sorted((node_dir(root) / "gloss").iterdir())
    code, out = run(capsys, "gloss", "file", str(stale), "--graph", str(root))
    assert code == 1 and out["ok"] is False
    assert [p["code"] for p in out["problems"]] == ["gloss-subject-mismatch"]
    assert sorted((node_dir(root) / "gloss").iterdir()) == before

    run(capsys, "gloss", "file", str(draft), "--graph", str(root))  # the head moves on
    second = tmp_path / "second.md"
    second.write_text(text + "A rival edit of the old head.\n", encoding="utf-8")
    code, out = run(capsys, "gloss", "file", str(second), "--graph", str(root))
    assert code == 1 and [p["code"] for p in out["problems"]] == ["record-not-head"]
    assert head in json.dumps(out)


def test_revise_an_explainer_and_start_a_chain(
    root: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """R12 for explainers: with no chain on the proof, revise writes a fresh explainer/v1 naming
    the node's Proof.lean with supersedes null; filed, it lands under explainer/."""
    draft = tmp_path / "explainer.md"
    code, out = run(
        capsys, "gloss", "revise", TARGET, f"explainer:{NODE}", "--graph", str(root),
        "--by", "carol", "--out", str(draft),
    )  # fmt: skip
    assert code == 0 and out["supersedes"] is None
    doc, body = glosses.split_front_matter(draft.read_text(encoding="utf-8"))
    assert (
        doc is not None and doc["schema"] == "explainer/v2"
    )  # F21-R6: revise writes what the service writes and doc["supersedes"] is None
    assert doc["proof"] == schemas.content_hash((node_dir(root) / "Proof.lean").read_bytes())
    assert body.lstrip().startswith("## ")
    code, out = run(capsys, "gloss", "file", str(draft), "--graph", str(root))
    assert code == 0, out
    [written] = out["written"]
    assert written.startswith(f"targets/{TARGET}/nodes/{NODE}/explainer/")
    assert classified(root, written) == []


def test_sign_writes_a_valid_gloss_signature(
    root: Path, key: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """AC10: sign writes a gloss signature the gate accepts; a gloss that is not there is
    refused with nothing written."""
    digest = seed_gloss(root)
    code, out = run(
        capsys, "gloss", "sign", TARGET, digest, "--graph", str(root), "--by", CURATOR,
        "--key", str(key), "--date", "2026-10-05T00:00:00Z",
    )  # fmt: skip
    assert code == 0 and out["ok"] is True
    [written] = out["written"]
    assert written.endswith(f"/gloss/signed/{digest}-1.yaml")
    doc = yaml.safe_load((root / written).read_text(encoding="utf-8"))
    assert doc["affirmation"] == glosses.AFFIRMATION and signed.verifies(
        doc, signed.default_signer()
    )
    assert classified(root, written, author=CURATOR) == []
    code, out = run(
        capsys, "gloss", "sign", TARGET, "f" * 64, "--graph", str(root), "--by", CURATOR,
        "--key", str(key),
    )  # fmt: skip
    assert code == 1 and out["ok"] is False and "nothing to sign" in out["refused"]


def test_sign_sections_writes_a_v2_signature_approving_them(
    root: Path, key: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """F21-R13 (T12): ``--sections`` names the section keys the signature approves and writes a
    v2 signature the gate accepts; a key the version lacks is refused with nothing written."""
    digest = seed_gloss(root)
    base = ["gloss", "sign", TARGET, digest, "--graph", str(root), "--by", CURATOR,
            "--key", str(key), "--date", "2026-10-06T00:00:00Z"]  # fmt: skip
    code, out = run(capsys, *base, "--sections", "whole")
    assert code == 0 and out["ok"] is True, out
    [written] = out["written"]
    doc = yaml.safe_load((root / written).read_text(encoding="utf-8"))
    assert doc["schema"] == "gloss-signature/v2" and doc["sections"] == ["whole"]
    assert classified(root, written, author=CURATOR) == []
    code, out = run(capsys, *base, "--sections", "overview")
    assert code == 1 and out["ok"] is False, out
    assert sorted(p.name for p in glosses.signed_dir(node_dir(root)).iterdir()) == [
        f"{digest}-1.yaml"
    ]


def test_section_keys_keep_a_steps_keys_own_commas() -> None:
    """``steps:s1,s2`` is one key: a part that starts no key continues the steps: key before it."""
    assert cli._section_keys("overview,steps:s1,s2,steps:s3") == [
        "overview", "steps:s1,s2", "steps:s3"
    ]  # fmt: skip
    assert cli._section_keys(" whole ") == ["whole"]


@pytest.mark.parametrize(
    "subject",
    ["statement:no-such-node", "nonsense", "relation:and-reassoc", f"explainer:{NODE}:{'f' * 64}"],
)
def test_revise_refuses_a_subject_that_is_not_there(
    root: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str], subject: str
) -> None:
    code, out = run(
        capsys, "gloss", "revise", TARGET, subject, "--graph", str(root), "--by", "carol",
        "--out", str(tmp_path / "x.md"),
    )  # fmt: skip
    assert code == 1 and out["ok"] is False and out["refused"]
    assert not (tmp_path / "x.md").exists()


def test_errors_never_escape_main(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """2026-09-10's sweep: a missing file or graph is exit 2 on stderr, not a traceback."""
    code = cli.main(["gloss", "file", str(tmp_path / "missing.md"), "--graph", str(tmp_path)])
    assert code == 2
    bad = tmp_path / "bad.md"
    bad.write_text("no front matter\n", encoding="utf-8")
    code = cli.main(["gloss", "file", str(bad), "--graph", str(tmp_path / "nope")])
    assert code == 2
    assert "opn-gate:" in capsys.readouterr().err
