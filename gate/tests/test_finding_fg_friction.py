"""Five small frictions a curator meets on the live graph (findings F1-F4 and G).

Each reported defect has a test asserting the behaviour the rules ask for; those fail today, and
each failure is the defect's own, not a setup error. Where the current behaviour is intended, or is
the guard a fix must not lose, a pinning test passes and quotes the rule it holds.

- F1  ``intake new`` without ``--spec`` compares a Mathlib-dependent pin across Mathlib pins
      (``cli.spec_template``; F11-R2, R6).
- F2  dormancy is judged at the wall clock while the record carries ``--date``
      (``cli.run_status`` / ``curator.declare_status``; D-33 (a), F08-R11).
- F3  a speculative crux's status record is stamped without the ``Z`` (``scaffold.files``).
- F4  ``intake activate`` writes over a status it should not flip (``intake.activate``; F11-R4, R5).
- G   root inference drops a revised root from its candidates and its message, and names
      ``target-status/v1`` (``graph.find_root``; F03-Q5, F08-Q16, F11-Q29).
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
import samples
import yaml
from harness import TARGET, copy_graph, take_in

from opn_gate import attestation, cli, curator, fidelity, intake, products, records, scaffold
from opn_gate import graph as graphmod

AUTHOR = "thisisanameforsure"


def run(capsys: pytest.CaptureFixture[str], *argv: str) -> tuple[int, dict[str, Any], str]:
    code = cli.main(list(argv))
    captured = capsys.readouterr()
    out: dict[str, Any] = json.loads(captured.out) if captured.out.strip() else {}
    return code, out, captured.err


# --- F1: the gate-spec template (F11-R2, R6) -----------------------------------------------------

MATHLIB_X = "0" * 40
MATHLIB_Y = "1" * 40
IMAGE_X = "ghcr.io/example/opn-gate@sha256:" + "b" * 64  # carries MATHLIB_X's oleans (R6)
IMAGE_PLAIN = "ghcr.io/example/opn-gate@sha256:" + "a" * 64  # no Mathlib, like the tutorial's
NEW = "erdos-3"


def put_spec(root: Path, target_id: str, **fields: Any) -> None:
    """A target's gate-spec.json: the fixture's own settings, with ``fields`` changed."""
    base = json.loads((root / "targets" / TARGET / "gate-spec.json").read_text())
    directory = root / "targets" / target_id
    directory.mkdir(parents=True, exist_ok=True)
    spec = {**base, "graph_id": target_id, **fields}
    (directory / "gate-spec.json").write_text(json.dumps(spec), encoding="utf-8")


def intake_new(
    capsys: pytest.CaptureFixture[str], root: Path, mathlib_sha: str
) -> tuple[int, dict[str, Any], str]:
    record = root.parent / f"{NEW}.yaml"
    coverage = {"mathlib_sha": mathlib_sha, "missing_prerequisites": []}
    record.write_text(yaml.safe_dump(samples.target_record(id=NEW, library_coverage=coverage)))
    node = root / "targets" / TARGET / "nodes" / "and-reassoc"
    return run(
        capsys,
        "intake", "new", NEW,
        "--graph", str(root), "--from", str(record), "--root", str(node),
        "--author", "curator", "--date", "2026-09-13T00:00:00Z", "--no-toolchain",
    )  # fmt: skip


def live_shaped_graph(tmp_path: Path) -> Path:
    """The live graph's shape: one Mathlib-free target on its own image (the tutorial) beside
    Mathlib-pinned targets that agree with each other on everything but their id."""
    root = copy_graph(tmp_path)
    put_spec(root, TARGET, mathlib_sha=None, devcontainer_ref=IMAGE_PLAIN)
    put_spec(root, "erdos-1", mathlib_sha=MATHLIB_X, devcontainer_ref=IMAGE_X)
    put_spec(root, "erdos-2", mathlib_sha=MATHLIB_X, devcontainer_ref=IMAGE_X)
    return root


@pytest.mark.xfail(
    strict=True,
    reason="finding F1 (F11-R2, R6): intake's spec template demands unanimity including the Mathlib-bound image digest",  # noqa: E501 — the xfail reason names the finding and its fix
)
def test_intake_inherits_the_image_of_the_targets_sharing_its_mathlib_pin(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """F1 (fails today). Live, every intake without ``--spec`` stops at "this graph's targets do
    not agree on one gate-spec; pass --spec", because the unanimity check compares
    ``devcontainer_ref`` across Mathlib pins. That field is not trust base: F11-R6 says
    "gate-spec.json shall name a per-graph image digest whose image contains that Mathlib's
    oleans", so it is a function of ``mathlib_sha``, which the check already excludes. The
    template's own reason
    ("a target quietly listed under a different allowlist would be a second trust base") is about
    the allowlist, the hazard checkers and the caps, and all of those agree here."""
    root = live_shaped_graph(tmp_path)
    code, _out, err = intake_new(capsys, root, MATHLIB_X)
    assert code == cli.EXIT_PASS, err
    spec = json.loads((root / "targets" / NEW / "gate-spec.json").read_text())
    assert spec["mathlib_sha"] == MATHLIB_X
    assert spec["devcontainer_ref"] == IMAGE_X


@pytest.mark.xfail(
    strict=True,
    reason="finding F1 (F11-R6): intake keeps another Mathlib's image digest under a new pin",
)
def test_intake_under_a_mathlib_pin_no_target_shares_needs_a_spec(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """F1's other half (fails today). When every target agrees, the template is taken whole and
    ``intake.spec_for`` swaps in the record's Mathlib SHA but keeps the template's image, so a
    target pinned to MATHLIB_Y is written to run on MATHLIB_X's image, against R6, and step 1's
    stamp check ("the image's Mathlib checkout is stamped ..., not ...") would refuse every gate
    run on it. No target in the graph can supply that image, so the curator has to (``--spec``)."""
    root = copy_graph(tmp_path)
    put_spec(root, TARGET, mathlib_sha=MATHLIB_X, devcontainer_ref=IMAGE_X)
    put_spec(root, "erdos-1", mathlib_sha=MATHLIB_X, devcontainer_ref=IMAGE_X)
    code, _out, err = intake_new(capsys, root, MATHLIB_Y)
    assert code != cli.EXIT_PASS, "a target was written under another Mathlib's image"
    assert "--spec" in err
    assert not (root / "targets" / NEW).exists()


def test_targets_disagreeing_on_the_trust_base_still_need_a_spec(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """F1 pin (passes). The unanimity rule is right about the trust base, and a fix must keep it:
    "the axiom allowlist, the hazard checkers and the step-3 caps are what the graph's own gate
    runs under (D-35), and a target quietly listed under a different allowlist would be a second
    trust base. With no single answer in the graph the curator has to say which one."""
    root = copy_graph(tmp_path)
    put_spec(root, TARGET, mathlib_sha=MATHLIB_X, devcontainer_ref=IMAGE_X)
    base = json.loads((root / "targets" / TARGET / "gate-spec.json").read_text())
    wider = [*base["axiom_allowlist"], "Lean.ofReduceBool"]
    put_spec(
        root, "erdos-1", mathlib_sha=MATHLIB_X, devcontainer_ref=IMAGE_X, axiom_allowlist=wider
    )
    code, _out, err = intake_new(capsys, root, MATHLIB_X)
    assert code != cli.EXIT_PASS and "--spec" in err
    assert not (root / "targets" / NEW).exists()


# --- F2: the reference time of D-33 (a) ----------------------------------------------------------

CLOCK = datetime(2026, 9, 13, 12, 0, 0, tzinfo=UTC)


def seed_git(root: Path, home: Path, when: str) -> None:
    """One commit touching every node, with committer time ``when`` (the last progress merge)."""
    env = {
        "GIT_AUTHOR_NAME": "curator",
        "GIT_AUTHOR_EMAIL": "c@x",
        "GIT_COMMITTER_NAME": "curator",
        "GIT_COMMITTER_EMAIL": "c@x",
        "GIT_AUTHOR_DATE": when,
        "GIT_COMMITTER_DATE": when,
        "PATH": "/usr/bin:/bin",
        "HOME": str(home),
    }
    for args in (["init", "-q"], ["add", "-A"], ["commit", "-q", "-m", "seed"]):
        subprocess.run(["git", "-C", str(root), *args], check=True, env=env, capture_output=True)


def declare_dormant(capsys: pytest.CaptureFixture[str], root: Path, date: str) -> int:
    code, _out, _err = run(
        capsys,
        "status", "--graph", str(root), "--author", AUTHOR, "--date", date,
        TARGET, "dormant", "--cause", "the network has moved on",
    )  # fmt: skip
    return code


@pytest.mark.xfail(
    strict=True,
    reason="finding F2 (D-33): dormancy is judged against the wall clock, not the record's --date",
)
def test_a_back_dated_dormancy_is_judged_at_its_own_date(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """F2 (fails today). D-33: a dormancy record "is valid only if it names the D-25 series values
    at declaration and ... (a) ... no progress artifact ... has landed on the target in N days".
    The record's ``date`` is the declaration's. ``run_status`` passes ``now=attestation.utc_now()``,
    so a record dated ten days after the last merge is accepted because the *clock* is 104 days
    after it: the record then says D-33 (a) held on a date when it did not. Whether the fix makes
    ``--date`` the reference or refuses a ``--date`` that differs from the clock, this record must
    not be written."""
    monkeypatch.setattr(attestation, "utc_now", lambda: CLOCK)
    root = copy_graph(tmp_path)
    seed_git(root, tmp_path, "2026-06-01T00:00:00Z")
    assert cli.last_progress_merge(root, TARGET) == datetime(2026, 6, 1, tzinfo=UTC)
    code = declare_dormant(capsys, root, "2026-06-11T00:00:00Z")
    assert code != cli.EXIT_PASS, "a dormancy dated 10 days after a merge was accepted"
    assert not (root / "targets" / TARGET / "status").exists()


def test_a_dormancy_dated_after_the_clock_does_not_open_the_window(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """F2 pin (passes). Whatever the reference becomes, a curator cannot reach D-33 (a)'s N days by
    writing a later ``--date``: the merge was three days ago on the clock. A future-dated record
    would also outrank every later record, since "latest by date then file name wins" (F03-Q5)."""
    monkeypatch.setattr(attestation, "utc_now", lambda: CLOCK)
    root = copy_graph(tmp_path)
    seed_git(root, tmp_path, "2026-09-10T00:00:00Z")
    code = declare_dormant(capsys, root, "2026-12-31T00:00:00Z")
    assert code != cli.EXIT_PASS
    assert not (root / "targets" / TARGET / "status").exists()


# --- F3: the speculative crux's record name ------------------------------------------------------

CRUX_DATE = "2026-09-13T12:00:00Z"  # the api's clock.render shape, second precision with Z


def crux(date: str = CRUX_DATE) -> scaffold.Proposal:
    return scaffold.Proposal(
        node_id="spec-crux",
        target_id=TARGET,
        statement="theorem OpnProp.crux : ∀ p : Prop, p → p := by\n  sorry\n",
        witness="theorem witness : True := trivial\n",
        author="prover-b",
        origin="authored",
        speculative=True,
        date=date,
    )


@pytest.mark.xfail(strict=True, reason="finding F3: a speculative crux's status stamp lacks its Z")
def test_a_speculative_crux_status_record_is_stamped_like_every_other_record() -> None:
    """F3 (fails today). Every other status record is ``<stamp>-<author>.yaml`` with
    ``curator.stamp``'s shape, ``20260910T121314Z`` ("sorts lexically, a legal file name");
    ``scaffold.files`` cuts its stamp at 15 characters and so drops the ``Z``."""
    files = scaffold.files(None, crux(), dep_statements={})
    written = sorted(k for k in files if k.startswith("status/"))
    expected = curator.record_path(Path("node"), author="prover-b", date=CRUX_DATE).name
    assert written == [f"status/{expected}"]  # 20260913T120000Z-prover-b.yaml


def test_the_missing_z_changes_order_only_within_one_second(tmp_path: Path) -> None:
    """F3 pin (passes): what the defect can and cannot do. Nothing parses these names; the only
    reader is ``records._latest_record``, which sorts by (date, file name) with a day-precision
    date, so the name decides within a day. A curator record one second later still wins over the
    crux's record, with or without the ``Z``. Only at the *same* second does ``-`` (0x2D) sort
    before ``Z`` (0x5A), putting the Z-less record first whatever its author's name."""
    node = tmp_path / "node"
    status = node / "status"
    status.mkdir(parents=True)
    spec_name = next(k for k in scaffold.files(None, crux(), dep_statements={}) if "status/" in k)
    (node / spec_name).write_text(yaml.safe_dump(scaffold.status_record(crux())))
    later = curator.node_status_doc("abandoned", "dead branch", author="a", date=CRUX_DATE)
    path = curator.record_path(node, author="a", date="2026-09-13T12:00:01Z")
    path.write_text(yaml.safe_dump(later))
    latest = records.load_node_status(node)
    assert latest is not None and latest.status == "abandoned"


# --- F4: activation writes over a status it should not flip (F11-R4, R5) --------------------------

LISTED = "euclid-primes"


def claimable_target(tmp_path: Path) -> Path:
    """A listed target that activation accepts: a non-author's signature and a posting (AC5)."""
    root = copy_graph(tmp_path)
    take_in(root)
    fidelity.attest(
        root / "targets" / LISTED,
        "root",
        "screened-and-signed",
        attestor="reviewer",
        date="2026-09-11",
        evidence="read the Lean against the English",
    )
    intake.post(
        root, LISTED, venue="v", url="https://example.org/posting", date="2026-09-12T00:00:00Z"
    )
    return root


def declare(root: Path, status: str, date: str) -> None:
    doc = intake.status_doc(
        status, f"{status} (test)", author="curator", date=date, root="and-reassoc"
    )
    stamp = curator.stamp(date)
    (root / "targets" / LISTED / "status" / f"{stamp}-curator.yaml").write_text(yaml.safe_dump(doc))


def index_row(root: Path) -> dict[str, Any]:
    prod = products.generate(root, rendered_from="5" * 40, commit_time="2026-09-13T00:00:00Z")
    docs = {p.as_posix(): json.loads(data) for p, data in prod.files.items()}
    return next(r for r in docs["targets/index.json"]["targets"] if r["target_id"] == LISTED)


def status_names(root: Path) -> list[str]:
    return sorted(p.name for p in (root / "targets" / LISTED / "status").iterdir())


@pytest.mark.xfail(
    strict=True, reason="finding F4 (F11-R5): activating an already-active target is not refused"
)
def test_activating_an_active_target_is_refused(tmp_path: Path) -> None:
    """F4 (fails today). R5: ``intake activate`` is "flipping status to active"; on a target already
    active there is nothing to flip, and today a second record is appended saying so. ``intake
    post``'s precedent is to refuse a restated fact ("a second one would silently replace the
    first"); here nothing is replaced, so this is append-only noise rather than corruption — the
    owner may prefer to keep it (see the report), in which case this test becomes a pin."""
    root = claimable_target(tmp_path)
    intake.activate(root, LISTED, author="curator", date="2026-09-12T00:00:00Z")
    before = status_names(root)
    with pytest.raises(intake.IntakeError, match="active"):
        intake.activate(root, LISTED, author="curator", date="2026-09-13T00:00:00Z")
    assert status_names(root) == before


@pytest.mark.xfail(
    strict=True, reason="finding F4 (F11-R4, D-33): intake activate reopens a known-result target"
)
def test_activation_does_not_reopen_a_known_result(tmp_path: Path) -> None:
    """F4, the sharper case (fails today). F11-R4: "listed, resolved and known-result close
    claiming". ``activate`` computes claimability *as if* the target were active and never reads
    its current status, so a target relabelled known-result (D-6's rediscovery relabel, D-33's
    set) is silently reopened: the products go from known-result / not claimable to active /
    claimable."""
    root = claimable_target(tmp_path)
    declare(root, "known-result", "2026-09-12T10:00:00Z")
    assert (index_row(root)["status"], index_row(root)["claimable"]) == ("known-result", False)
    with pytest.raises(intake.IntakeError):
        intake.activate(root, LISTED, author="curator", date="2026-09-13T00:00:00Z")
    assert (index_row(root)["status"], index_row(root)["claimable"]) == ("known-result", False)


def test_activating_a_dormant_target_is_allowed(tmp_path: Path) -> None:
    """F4 pin (passes). A fix must not refuse every status but ``listed``: D-33's dormancy is
    "evidence-gated, reversible, and closes nothing", so a curator taking a dormant target back to
    active is a real flip and is written, carrying the root (R14)."""
    root = claimable_target(tmp_path)
    declare(root, "dormant", "2026-09-12T10:00:00Z")
    (written,) = intake.activate(root, LISTED, author="curator", date="2026-09-13T00:00:00Z")
    doc = yaml.safe_load((root / written).read_text())
    assert doc["status"] == "active" and doc["root"] == "and-reassoc"
    assert index_row(root)["status"] == "active"


# --- G: root inference's candidates and message (F03-Q5, F08-Q16, F11-Q29) ------------------------


@pytest.fixture
def facts(tmp_path: Path) -> Any:
    tg = graphmod.load_target(copy_graph(tmp_path), TARGET)

    def make(node_id: str, base: str = "and-reassoc", **kw: Any) -> graphmod.NodeFacts:
        return replace(tg.nodes[base], node_id=node_id, **{"deps": (), **kw})

    return make


def superseded_by(successor: str) -> records.StatusRecord:
    doc = {"status": "superseded", "reference": successor}
    return records.StatusRecord("superseded", "curator", "2026-09-10", Path("x"), doc)


@pytest.mark.xfail(
    strict=True, reason="finding G: the root-ambiguity message cites target-status/v1"
)
def test_root_ambiguity_names_the_current_target_status_schema(facts: Any) -> None:
    """G (fails today). The message tells the curator to write "target-status/v1 root", but every
    writer writes ``target-status/v2`` (``intake.TARGET_STATUS_SCHEMA``; F11-R12), and v2 is what a
    curator should copy."""
    nodes = {"a": facts("a"), "v": facts("v", base="tutorial-and-swap")}
    with pytest.raises(graphmod.GraphError, match="root is ambiguous") as refused:
        graphmod.find_root(nodes, None)
    message = str(refused.value)
    assert intake.TARGET_STATUS_SCHEMA in message
    assert "target-status/v1" not in message


@pytest.mark.xfail(
    strict=True, reason="finding G: the root-ambiguity message omits the revision it set aside"
)
def test_root_ambiguity_lists_the_revision_it_set_aside(facts: Any) -> None:
    """G (fails today). With the root revised (``a`` superseded by ``a-v2``) and two variants
    merged, the message reads "2 nodes have no dependents (v, w)": ``a-v2``, the node that should
    be the root, is set aside as "a revision of an interior node" and so is missing from the one
    line the curator reads to write the declaration."""
    nodes = {
        "a": facts("a", override=superseded_by("a-v2")),
        "a-v2": facts("a-v2", supersedes="a"),
        "v": facts("v", base="tutorial-and-swap"),
        "w": facts("w", base="tutorial-and-swap"),
    }
    with pytest.raises(graphmod.GraphError, match="root is ambiguous") as refused:
        graphmod.find_root(nodes, None)
    for candidate in ("a-v2", "v", "w"):
        assert candidate in str(refused.value)


@pytest.mark.xfail(
    strict=True,
    reason="finding G (C7): a variant beside a revised root is silently inferred as the root",
)
def test_a_variant_beside_a_revised_root_is_not_inferred_as_the_root(facts: Any) -> None:
    """G, the silent case (fails today). The same filter with *one* variant leaves one sink, and
    ``find_root`` returns the variant as the target's root: no error, and the products would
    publish it (and derive ``resolved`` from it). Reachable on an undeclared pre-F11 target whose
    root is revised before its first variant merges. C7: "never fail silently"; ``_current_node``'s
    own docstring calls publishing the wrong root "a silent wrong answer"."""
    nodes = {
        "a": facts("a", override=superseded_by("a-v2")),
        "a-v2": facts("a-v2", supersedes="a"),
        "v": facts("v", base="tutorial-and-swap"),
    }
    with pytest.raises(graphmod.GraphError, match="root is ambiguous") as refused:
        root = graphmod.find_root(nodes, None)
        pytest.fail(f"inferred {root!r} as the root")
    assert "a-v2" in str(refused.value) and "v" in str(refused.value)


def test_revisions_are_still_set_aside_where_f08_q16_meant_them(facts: Any) -> None:
    """G pin (passes). F08-Q16: "a revised interior node does not make the root ambiguous and a
    revised root becomes the root". A fix for the case above must keep both."""
    interior = {
        "a": facts("a", deps=("b",)),
        "b": facts("b", override=superseded_by("b-v2")),
        "b-v2": facts("b-v2", supersedes="b"),
    }
    assert graphmod.find_root(interior, None) == "a"
    revised_root = {
        "a": facts("a", override=superseded_by("a-v2")),
        "a-v2": facts("a-v2", supersedes="a"),
    }
    assert graphmod.find_root(revised_root, None) == "a-v2"
