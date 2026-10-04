"""F07-T65: ``reproduce`` and ``postmerge`` refuse a network checkout that is not the spec's pin.

The finding (audit 2026-10-04). An attestation copies ``network_commit`` from the target's
``gate-spec.json`` (``attestation.build``), and nothing compared that with the gate actually
running. ``reproduce.sh`` run from any checkout of this repository — a later ``main``, a branch,
a working tree with ``gate/`` edited — produced a record naming the pinned gate, and
``--compare`` could answer ``identical: true`` for a replay the pinned gate never made. D-5's
"two runs anywhere agree" is a claim about *the pinned gate*; a run of another gate says nothing
about it.

The rule. ``reproduce`` reads the pin from git before exporting anything and refuses with
``network-mismatch`` (exit 2, nothing built) when the running checkout's ``HEAD`` differs, when
``gate/`` is dirty, or when the gate is not running from a git checkout at all.
``--allow-network-mismatch`` runs anyway, says so, and a ``--compare`` result is then never
``identical``. ``postmerge`` refuses only when the job declares the commit it checked out
(``OPN_NETWORK_COMMIT``) and the running one differs; the graph's workflow does not set it yet,
so its runs are unchanged until it does.

The running checkout is the seam ``cli.running_network_commit``; every test here sets it (the
autouse fixture in ``conftest.py`` puts every other test at the fixtures' forty-zero pin).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from harness import TARGET, TUTORIAL
from test_cli_sandboxed import Seam, git_repo, run

from opn_gate import cli, postmerge, schemas

PIN = "0" * 40  # what every fixture graph's gate-spec.json pins
OTHER = "a" * 40
#: The real seam, taken at import, before conftest's autouse fixture replaces it for each test.
REAL_SEAM = cli.running_network_commit


def at(monkeypatch: pytest.MonkeyPatch, commit: str | None, *dirty: str) -> None:
    monkeypatch.setattr(cli, "running_network_commit", lambda: cli.RunningNetwork(commit, dirty))


def reproduce_argv(root: Path, head: str, out: Path, *extra: str) -> list[str]:
    return [
        "reproduce", "--graph", str(root), "--commit", head, "--node", TUTORIAL,
        "--out", str(out), *extra,
    ]  # fmt: skip


def postmerge_argv(root: Path, head: str, out: Path) -> list[str]:
    return [
        "postmerge", "--graph", str(root), "--commit", head, "--pr", "1",
        "--review-kind", "tutorial", "--target", TARGET, "--node", TUTORIAL, "--out", str(out),
    ]  # fmt: skip


def test_reproduce_refuses_another_commit_before_building_anything(
    tmp_path: Path, seam: Seam, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    root, git, _base = git_repo(tmp_path)
    head = git("rev-parse", "HEAD")
    at(monkeypatch, OTHER)
    code, out, err = run(capsys, *reproduce_argv(root, head, tmp_path / "o"))
    assert code == cli.EXIT_ERROR, (out, err)
    assert out.get("verdict") == "refused"
    diagnostic = out["diagnostic"]
    assert diagnostic["code"] == "network-mismatch"
    assert diagnostic["details"]["pinned"] == PIN and diagnostic["details"]["running"] == OTHER
    assert "network" in err
    assert seam.made == [] and seam.docker_log() == []  # no image, no sandbox
    assert not (tmp_path / "o" / "tree").exists()  # no export


def test_reproduce_refuses_a_dirty_gate_at_the_pin(
    tmp_path: Path, seam: Seam, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    root, git, _base = git_repo(tmp_path)
    at(monkeypatch, PIN, "gate/opn_gate/steps/axioms.py")
    code, out, _err = run(capsys, *reproduce_argv(root, git("rev-parse", "HEAD"), tmp_path / "o"))
    assert code == cli.EXIT_ERROR
    assert out["diagnostic"]["code"] == "network-mismatch"
    assert out["diagnostic"]["details"]["dirty"] == ["gate/opn_gate/steps/axioms.py"]
    assert seam.made == []


def test_reproduce_refuses_a_gate_that_is_not_a_git_checkout(
    tmp_path: Path, seam: Seam, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    root, git, _base = git_repo(tmp_path)
    at(monkeypatch, None)
    code, out, _err = run(capsys, *reproduce_argv(root, git("rev-parse", "HEAD"), tmp_path / "o"))
    assert code == cli.EXIT_ERROR
    assert out["diagnostic"]["code"] == "network-mismatch"
    assert out["diagnostic"]["details"]["running"] is None
    assert seam.made == []


def test_reproduce_at_the_pin_runs_as_before(
    tmp_path: Path, seam: Seam, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    root, git, _base = git_repo(tmp_path)
    at(monkeypatch, PIN)
    code, out, err = run(capsys, *reproduce_argv(root, git("rev-parse", "HEAD"), tmp_path / "o"))
    assert code == cli.EXIT_PASS and err == "", err
    assert out["verdict"] == "pass"


def test_allow_network_mismatch_reports_it_and_is_never_identical(
    tmp_path: Path, seam: Seam, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The record a replay compares against was made at the pin; a replay from elsewhere that
    differs in no field has still not reproduced it."""
    root, git, _base = git_repo(tmp_path)
    head = git("rev-parse", "HEAD")
    at(monkeypatch, PIN)
    code, first, _err = run(capsys, *reproduce_argv(root, head, tmp_path / "o1"))
    assert code == cli.EXIT_PASS
    committed = postmerge.record_step9(
        schemas.load_json(Path(first["attestation"])),
        merge_commit=head,
        review=postmerge.review_block("tutorial"),
    )
    committed_path = tmp_path / "000001.json"
    committed_path.write_bytes(schemas.canonical_json(committed))

    at(monkeypatch, OTHER)
    code, out, err = run(
        capsys,
        *reproduce_argv(
            root, head, tmp_path / "o2", "--compare", str(committed_path),
            "--allow-network-mismatch",
        ),
    )  # fmt: skip
    assert code == cli.EXIT_FAIL, (out, err)
    assert out["identical"] is False and out["differing_fields"] == []
    assert out["network_mismatch"]["code"] == "network-mismatch"
    assert "allow-network-mismatch" in err


def test_postmerge_refuses_when_the_job_declares_another_commit(
    tmp_path: Path, seam: Seam, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    root, git, _base = git_repo(tmp_path)
    at(monkeypatch, OTHER)
    monkeypatch.setenv("OPN_NETWORK_COMMIT", PIN)
    code, out, _err = run(capsys, *postmerge_argv(root, git("rev-parse", "HEAD"), tmp_path / "p"))
    assert code == cli.EXIT_ERROR
    assert out.get("verdict") == "refused"
    assert out["diagnostic"]["code"] == "network-mismatch"
    assert out["diagnostic"]["details"] == {"pinned": PIN, "running": OTHER, "dirty": []}
    assert seam.made == [] and not (tmp_path / "p" / "attestation.json").exists()


def test_postmerge_without_the_declaration_is_unchanged(
    tmp_path: Path, seam: Seam, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The graph's workflow does not set ``OPN_NETWORK_COMMIT`` today; its runs must not change
    until a re-pin makes it set it."""
    root, git, _base = git_repo(tmp_path)
    at(monkeypatch, OTHER, "gate/x.py")
    monkeypatch.delenv("OPN_NETWORK_COMMIT", raising=False)
    code, out, err = run(capsys, *postmerge_argv(root, git("rev-parse", "HEAD"), tmp_path / "p"))
    assert code == cli.EXIT_PASS, err
    assert out["verdict"] == "pass"


def test_postmerge_with_the_matching_declaration_runs(
    tmp_path: Path, seam: Seam, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    root, git, _base = git_repo(tmp_path)
    at(monkeypatch, PIN)
    monkeypatch.setenv("OPN_NETWORK_COMMIT", PIN)
    code, out, err = run(capsys, *postmerge_argv(root, git("rev-parse", "HEAD"), tmp_path / "p"))
    assert code == cli.EXIT_PASS, err
    assert out["verdict"] == "pass"


def test_the_seam_reads_this_checkout() -> None:
    """The real seam answers this repository's HEAD, which is what a refusal names."""
    got = REAL_SEAM()
    assert isinstance(got, cli.RunningNetwork)
    assert got.commit is not None and len(got.commit) == 40
