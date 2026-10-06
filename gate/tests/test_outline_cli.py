"""F19-T4, T5: ``opn-gate outline`` outlines every merged proof artifact that has none (R5, R6).

The command the graph's ``outline`` job and the backfill workflow both run. For a graph commit
and a target (or ``--all``) it finds every merged proof artifact — each node's ``Proof.lean``, each
alternate under ``attempts/`` and each merged partial assembly (F19-Q9) — that has no
``targets/<id>/outlines/<artifact-hash>.json`` yet, builds what the artifact imports exactly as
step 4 stages it (the dependency closure, the definitions, the node's own Context), runs
``opn-outline`` over it in the step-3 sandbox, and writes the outline. A partial's ``sorry`` steps
take their child nodes from F18's decompositions. A failure writes nothing for that artifact,
names it with its reason, and stops no other (R5, C7). Its report is one JSON document.

Fast tier: the sandbox the CLI constructs is the stand-in ``test_cli_sandboxed`` uses, whose
processes are a fake seam; ``test_outline_cli_real`` (lean tier) runs the real program over a
Lean-core fixture graph holding a proof, an alternate and a two-hole partial.
"""

from __future__ import annotations

import json
import re
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest
from fakes import FakeToolchain
from harness import TARGET, copy_graph
from test_cli_sandboxed import Seam, run
from test_decompositions import HOLE_IDS, PARTIAL, add_hole, merged_partial
from test_node_proofs import A, B, proof_hash, proved_interior
from test_outline import step
from test_products import ROOT_NODE, attest, nodes_dir

from opn_gate import config, outline, sandbox, schemas
from opn_gate.toolchain import ElabResult, MetaprogramResult, OutlineRequest, ResolvedToolchain

ALTERNATE = "attempts/20260930T120000Z-bob-alternate.lean"
SHA = re.compile(r"^[0-9a-f]{40}$")


# --- the fixture graph: three proofs, an alternate and a partial, committed ----------------------


def git(root: Path, *args: str) -> str:
    env = config.child_environment(
        {
            "GIT_AUTHOR_NAME": "t",
            "GIT_AUTHOR_EMAIL": "t@x",
            "GIT_COMMITTER_NAME": "t",
            "GIT_COMMITTER_EMAIL": "t@x",
        },
        drop=config.GIT_REPO_VARIABLES,
    )
    return subprocess.run(
        ["git", "-C", str(root), *args], check=True, env=env, capture_output=True, text=True
    ).stdout.strip()


def commit_all(root: Path, message: str = "seed") -> str:
    """Commit the tree as it is; an empty directory a node must have (``attempts/``, ``annex/``)
    keeps a ``.gitkeep``, as the graph's do, since git stores no empty directory."""
    for d in [p for p in root.rglob("*") if p.is_dir() and ".git" not in p.parts]:
        if not any(d.iterdir()):
            (d / ".gitkeep").write_text("", encoding="utf-8")
    if not (root / ".git").exists():
        git(root, "init", "-q")
    git(root, "add", "-A")
    git(root, "commit", "-q", "--allow-empty", "-m", message)
    return git(root, "rev-parse", "HEAD")


def merged_graph(tmp_path: Path) -> Path:
    """The propositional fixture with every kind of merged proof artifact: the two interior
    nodes' proofs, the root's proof, an alternate of the root and a two-hole partial of it — and
    ``targets/index.json`` beside the target directories, as the live graph has (2026-09-18)."""
    root = copy_graph(tmp_path, publish=True)
    proved_interior(root)
    attest(root, ROOT_NODE, n=3, artifact_hash=proof_hash(root, ROOT_NODE), footprint=None)
    node = nodes_dir(root) / ROOT_NODE
    alt = node / ALTERNATE
    alt.parent.mkdir(exist_ok=True)
    alt.write_text((node / "Proof.lean").read_text() + "\n-- again\n", encoding="utf-8")
    attest(root, ROOT_NODE, n=4, artifact_hash=schemas.content_hash(alt.read_bytes()))
    add_hole(root, HOLE_IDS[0], "hden")
    add_hole(root, HOLE_IDS[1], "hrem")
    merged_partial(root, 7, ["hden", "hrem"])
    (root / "targets" / "index.json").write_text("{}\n", encoding="utf-8")
    commit_all(root)
    return root


def file_hash(root: Path, node: str, path: str) -> str:
    return schemas.content_hash((nodes_dir(root) / node / path).read_bytes())


def expected(root: Path) -> list[tuple[str, str, str]]:
    """(node, path, hash) of every merged proof artifact of the fixture, sorted."""
    return sorted(
        [
            (ROOT_NODE, "Proof.lean", file_hash(root, ROOT_NODE, "Proof.lean")),
            (ROOT_NODE, ALTERNATE, file_hash(root, ROOT_NODE, ALTERNATE)),
            (ROOT_NODE, PARTIAL, file_hash(root, ROOT_NODE, PARTIAL)),
            (B, "Proof.lean", file_hash(root, B, "Proof.lean")),
            (A, "Proof.lean", file_hash(root, A, "Proof.lean")),
        ]
    )


def triples(entries: list[dict[str, Any]]) -> list[tuple[str, str, str]]:
    return sorted((e["node"], e["path"], e["artifact_hash"]) for e in entries)


def outlines_dir(root: Path) -> Path:
    return root / "targets" / TARGET / "outlines"


# --- the fake seam: answers per artifact, fails where it is told to ----------------------------


@dataclass
class Fake(FakeToolchain):
    """``opn-outline`` answers for the file it is given: a partial's ``sorry`` lines are hole
    steps named after the ``have`` they close, anything else one term step. ``fail_on`` is text
    whose presence in the artifact makes the program refuse it; ``fail_build`` the modules
    whose compile fails."""

    fail_on: str | None = None
    fail_build: frozenset[str] = frozenset()
    seen_files: list[str] = field(default_factory=list)

    def elaborate(
        self,
        tc: ResolvedToolchain,
        source: Path,
        module: str,
        out_dir: Path,
        *,
        root: Path | None = None,
        timeout_s: float | None = None,
    ) -> ElabResult:
        if module in self.fail_build:
            self.calls.append(f"elaborate:{module}")
            return ElabResult(ok=False, stderr=f"{module}: unknown identifier")
        return super().elaborate(tc, source, module, out_dir, root=root, timeout_s=timeout_s)

    def outline(
        self,
        tc: ResolvedToolchain,
        req: OutlineRequest,
        search_path: Sequence[Path],
        *,
        timeout_s: float | None = None,
    ) -> MetaprogramResult:
        self.calls.append(f"outline:{req.module}:{req.decl}")
        self.outline_requests.append(req)
        text = req.file.read_text(encoding="utf-8")
        self.seen_files.append(text)
        if self.fail_on is not None and self.fail_on in text:
            return MetaprogramResult(ok=False, doc={"ok": False, "error": "does not elaborate"})
        if "sorry" in text:
            steps = [
                step("hole", name, (2, 2), closed=("hole", []), claim="True")
                for name in ("hden", "hrem")
            ]
        else:
            steps = [step("term", None, (1, 1), closed=("term", []), claim="True")]
        return MetaprogramResult(
            ok=True, doc={"ok": True, "decl": req.decl, "steps": steps, "constants": {}}
        )


def outline_cli(capsys: pytest.CaptureFixture[str], *argv: str) -> tuple[int, dict[str, Any]]:
    code, doc, _err = run(capsys, "outline", *argv)
    return code, doc


# --- the tests ----------------------------------------------------------------------------------


def test_every_merged_artifact_is_outlined_once(
    tmp_path: Path, seam: Seam, capsys: pytest.CaptureFixture[str]
) -> None:
    """R1, R6, Q9: the root's proof, its alternate and its partial, and both interior proofs,
    each outlined from its own bytes in the sandbox and written under its own hash."""
    root = merged_graph(tmp_path)
    seam.fake = Fake()
    code, report = outline_cli(
        capsys, "--graph", str(root), "--target", TARGET, "--out", str(tmp_path / "o")
    )
    assert code == 0, report["failed"]
    assert triples(report["written"]) == expected(root)
    assert report["present"] == [] and report["failed"] == []
    assert SHA.match(report["gate"]) and report["commit"] == git(root, "rev-parse", "HEAD")

    written = sorted(p.name for p in outlines_dir(root).iterdir())
    assert written == sorted(f"{h}.json" for _n, _p, h in expected(root))
    by_path = {}
    for node, path, digest in expected(root):
        doc = schemas.validate(
            json.loads((outlines_dir(root) / f"{digest}.json").read_text()), "outline/v1"
        )
        assert (doc["target"], doc["node"]) == (TARGET, node)
        assert doc["artifact"]["path"] == path and doc["artifact"]["hash"] == digest
        assert doc["gate"] == report["gate"]
        by_path[(node, path)] = doc
    kinds = {k: d["artifact"]["kind"] for k, d in by_path.items()}
    assert kinds[(ROOT_NODE, ALTERNATE)] == "alternate"
    assert kinds[(ROOT_NODE, PARTIAL)] == "partial"
    assert kinds[(ROOT_NODE, "Proof.lean")] == kinds[(A, "Proof.lean")] == "proof"
    # Q9: the partial's sorry steps name the children F18's decompositions give them.
    holes = by_path[(ROOT_NODE, PARTIAL)]["steps"]
    assert [(s["kind"], s["child_node"]) for s in holes] == [
        ("hole", HOLE_IDS[0]),
        ("hole", HOLE_IDS[1]),
    ]
    # Each artifact was outlined as the node's own Proof module, from its own bytes.
    fake = seam.fake
    assert isinstance(fake, Fake)
    modules = {r.module for r in fake.outline_requests}
    assert modules == {f"Nodes.«{n}».Proof" for n in (ROOT_NODE, A, B)}
    root_dir = nodes_dir(root) / ROOT_NODE
    for path in ("Proof.lean", ALTERNATE, PARTIAL):
        assert (root_dir / path).read_text(encoding="utf-8") in fake.seen_files
    # Only in the sandbox (R6): every container was given its work directory and nothing else.
    assert seam.made, "no sandbox was constructed"
    work = (tmp_path / "o").resolve()
    for made in seam.made:
        assert made["read_only"] == []
        assert all(p.is_relative_to(work) for p in made["read_write"]), made


def test_an_outline_already_there_is_not_extracted_again(
    tmp_path: Path, seam: Seam, capsys: pytest.CaptureFixture[str]
) -> None:
    """The job runs after every building merge: what has an outline costs nothing, not even an
    image (a Mathlib image is gigabytes, 2026-09-13)."""
    root = merged_graph(tmp_path)
    seam.fake = Fake()
    outline_cli(capsys, "--graph", str(root), "--target", TARGET, "--out", str(tmp_path / "o1"))
    commit_all(root, "outlines")
    seam.made.clear()
    log_before = len(seam.docker_log())
    seam.fake = Fake()
    code, report = outline_cli(
        capsys, "--graph", str(root), "--target", TARGET, "--out", str(tmp_path / "o2")
    )
    assert code == 0
    assert report["written"] == [] and report["failed"] == []
    assert triples(report["present"]) == expected(root)
    assert seam.fake.outline_requests == [] and seam.fake.calls == []
    assert seam.made == [] and len(seam.docker_log()) == log_before


def assert_failed_exactly(root: Path, report: dict[str, Any], failed: set[tuple[str, str]]) -> None:
    """The report names exactly ``failed``, nothing is written for any of them, and every other
    artifact was written."""
    named = {(e["node"], e["path"]) for e in report["failed"]}
    assert named == failed, report["failed"]
    assert triples(report["written"]) == [t for t in expected(root) if (t[0], t[1]) not in failed]
    names = {p.name for p in outlines_dir(root).iterdir()}
    for node, path in failed:
        assert f"{file_hash(root, node, path)}.json" not in names


def test_one_failure_writes_nothing_and_stops_nothing(
    tmp_path: Path, seam: Seam, capsys: pytest.CaptureFixture[str]
) -> None:
    """R5, AC5: the program refuses the alternate; it is named with its reason, nothing is
    written for it, and every other artifact is outlined. Exit 1 says the report has a failure."""
    root = merged_graph(tmp_path)
    seam.fake = Fake(fail_on="-- again")
    code, report = outline_cli(
        capsys, "--graph", str(root), "--target", TARGET, "--out", str(tmp_path / "o")
    )
    assert code == 1
    assert_failed_exactly(root, report, {(ROOT_NODE, ALTERNATE)})
    [bad] = report["failed"]
    assert bad["reason"] == outline.FAILED and "does not elaborate" in bad["detail"]


def test_a_build_failure_names_every_artifact_that_imports_it(
    tmp_path: Path, seam: Seam, capsys: pytest.CaptureFixture[str]
) -> None:
    """R5: B's Context does not compile, so neither B's proof nor any of the root's three
    artifacts (which rest on B) can be built; each is named with the module that failed, and
    the tutorial node's proof, which does not rest on B, is still outlined."""
    root = merged_graph(tmp_path)
    seam.fake = Fake(fail_build=frozenset({f"Nodes.«{B}».Context"}))
    code, report = outline_cli(
        capsys, "--graph", str(root), "--target", TARGET, "--out", str(tmp_path / "o")
    )
    assert code == 1
    assert_failed_exactly(
        root,
        report,
        {
            (B, "Proof.lean"),
            (ROOT_NODE, "Proof.lean"),
            (ROOT_NODE, ALTERNATE),
            (ROOT_NODE, PARTIAL),
        },
    )
    for e in report["failed"]:
        assert e["reason"] == "build-failed"
        assert f"Nodes.«{B}».Context does not elaborate" in e["detail"], e


def test_all_targets_and_a_separate_destination(
    tmp_path: Path, seam: Seam, capsys: pytest.CaptureFixture[str]
) -> None:
    """``--all`` takes the targets that have a gate-spec.json (``index.json`` is not one), and
    ``--dest`` writes the outlines beside the checkout, never into it — the backfill's shape, so
    the artifact a curator downloads holds only what was new (R7)."""
    root = merged_graph(tmp_path)
    dest = tmp_path / "dest"
    seam.fake = Fake()
    code, report = outline_cli(
        capsys, "--graph", str(root), "--all", "--dest", str(dest), "--out", str(tmp_path / "o")
    )
    assert code == 0, report["failed"]
    assert report["targets"] == [TARGET]
    assert triples(report["written"]) == expected(root)
    assert not outlines_dir(root).exists()
    assert len(list((dest / "targets" / TARGET / "outlines").iterdir())) == len(expected(root))
    # A second run against the same destination finds every one there.
    seam.fake = Fake()
    code, again = outline_cli(
        capsys, "--graph", str(root), "--all", "--dest", str(dest), "--out", str(tmp_path / "o2")
    )
    assert code == 0 and again["written"] == [] and len(again["present"]) == len(expected(root))


def test_a_target_that_cannot_be_read_is_named_and_the_rest_are_outlined(
    tmp_path: Path, seam: Seam, capsys: pytest.CaptureFixture[str]
) -> None:
    """One target's defect never decides whether the others get outlines (the 2026-09-17 rule)."""
    root = merged_graph(tmp_path)
    broken = root / "targets" / "broken"
    (broken / "nodes").mkdir(parents=True)
    (broken / "gate-spec.json").write_text("{not json", encoding="utf-8")
    commit_all(root, "a broken target")
    seam.fake = Fake()
    code, report = outline_cli(capsys, "--graph", str(root), "--all", "--out", str(tmp_path / "o"))
    assert code == 1
    assert report["targets"] == ["broken", TARGET]
    [bad] = report["failed"]
    assert bad["target"] == "broken" and bad["node"] is None
    assert bad["reason"] == "target-unreadable"
    assert triples(report["written"]) == expected(root)


def test_usage_errors_are_exit_two_before_any_work(
    tmp_path: Path, seam: Seam, capsys: pytest.CaptureFixture[str]
) -> None:
    root = merged_graph(tmp_path)
    with pytest.raises(SystemExit) as exc:  # neither --target nor --all
        outline_cli(capsys, "--graph", str(root))
    assert exc.value.code == 2
    code, _ = outline_cli(capsys, "--graph", str(root), "--target", "no-such-target")
    assert code == 2
    code, _ = outline_cli(capsys, "--graph", str(tmp_path / "nowhere"), "--all")
    assert code == 2
    assert seam.made == []


# --- the lean tier: the real program over a Lean-core graph -------------------------------------


REAL_PARTIAL = "attempts/20261004T000000Z-carol-partial.lean"


@pytest.mark.lean
def test_outline_cli_real(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    real_toolchain: Any,
    lean_pkg: Path,
) -> None:
    """The command end to end on the real toolchain: the fixture's root proof, an alternate of
    it, and a two-hole partial of it, each built against the interior nodes' merged proofs and
    outlined by ``opn-outline``. The sandbox is the host toolchain here (the docker tier owns
    the container); everything else is the command as the job runs it."""
    from opn_gate.toolchain import LocalToolchain  # noqa: PLC0415

    root = copy_graph(tmp_path / "g", publish=True)
    proved_interior(root)
    attest(root, ROOT_NODE, n=3, artifact_hash=proof_hash(root, ROOT_NODE), footprint=None)
    node = nodes_dir(root) / ROOT_NODE
    proof = (node / "Proof.lean").read_text(encoding="utf-8")
    body = "  exact ⟨h2.2.2, OpnProp.and_swap p q h.1⟩\n"
    assert body in proof  # guard: the fixture's proof still ends this way
    alternate = proof.replace(body, "  exact ⟨h2.2.2, h2.2.1, h2.1⟩\n")
    (node / "attempts").mkdir(exist_ok=True)
    (node / ALTERNATE).write_text(alternate, encoding="utf-8")
    attest(root, ROOT_NODE, n=4, artifact_hash=schemas.content_hash(alternate.encode()))
    # A two-hole partial of the root: the same proof with its last two facts left as holes.
    head, _sep, _rest = proof.partition(body)
    partial = (
        head + "  have hden : r := sorry\n  have hrem : q ∧ p := sorry\n  exact ⟨hden, hrem⟩\n"
    )
    add_hole(root, HOLE_IDS[0], "hden")
    add_hole(root, HOLE_IDS[1], "hrem")
    merged_partial(root, 7, ["hden", "hrem"], path=REAL_PARTIAL, annex=None)
    (node / REAL_PARTIAL).write_text(partial, encoding="utf-8")
    commit_all(root)

    seam_tc = LocalToolchain(real_toolchain.elan, lean_pkg)

    def make_sandbox(
        image: str,
        caps: sandbox.Caps,
        *,
        read_only: Sequence[Path] = (),
        read_write: Sequence[Path] = (),
    ) -> LocalToolchain:
        return seam_tc

    monkeypatch.setattr(sandbox, "SandboxToolchain", make_sandbox)
    code, doc, err = run(
        capsys,
        "outline",
        "--graph",
        str(root),
        "--target",
        TARGET,
        "--image",
        "opn-test:host",
        "--out",
        str(tmp_path / "o"),
    )
    assert code == 0, (doc, err)
    wanted = {
        (ROOT_NODE, "Proof.lean"),
        (ROOT_NODE, ALTERNATE),
        (ROOT_NODE, REAL_PARTIAL),
        (A, "Proof.lean"),
        (B, "Proof.lean"),
    }
    assert {(e["node"], e["path"]) for e in doc["written"]} == wanted, doc
    out = outlines_dir(root)
    docs = {
        (d["node"], d["artifact"]["path"]): d
        for d in (json.loads(p.read_text()) for p in sorted(out.iterdir()))
    }
    assert set(docs) == wanted
    holes = [s for s in docs[(ROOT_NODE, REAL_PARTIAL)]["steps"] if s["kind"] == "hole"]
    assert [(s["name"], s["child_node"]) for s in holes] == [
        ("hden", HOLE_IDS[0]),
        ("hrem", HOLE_IDS[1]),
    ]
    # Each was elaborated against the interior nodes' merged proofs: the `have h2` step of the
    # proof and of the alternate uses and-reassoc's theorem, read back as a use of that node (a
    # use in the closing `exact` belonged to no step, F19-Q11 (7), until F22-T14 made the trailing
    # closing tactics the `close` step).
    for path in ("Proof.lean", ALTERNATE):
        steps = docs[(ROOT_NODE, path)]["steps"]
        assert [(s["id"], s["name"]) for s in steps] == [("h2", "h2"), ("close", None)], steps
        assert steps[0]["uses"]["nodes"] == [B], steps[0]["uses"]
    assert (
        docs[(ROOT_NODE, "Proof.lean")]["artifact"]["hash"]
        != (docs[(ROOT_NODE, ALTERNATE)]["artifact"]["hash"])
    )
