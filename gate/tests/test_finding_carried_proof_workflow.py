"""F32-T5 (R5, R8, AC8; D-5 v3.49, C8): the graph workflow signs every attestation the
re-derivation wrote, and the catch-up record carries the born-proved holes'.

Read from ``gate.yml`` on the refs the merge actor's tests read (``f32-t5-gate`` first while it is a
graph branch). Since F32-T3 the re-derivation leaves each born-proved hole's unsigned record at
``<out>/hole-attestations/<hole id>.json``; the one key step signs each into
``attestations/<NNNNNN>.<hole id>.json`` (``postmerge.hole_attestation_path``, Q7), beside the
partial's own ``attestations/<NNNNNN>.json``. Checked where each property is enforced: the key
step is still the only step that names the key and nothing before it is granted any secret; the
closure sweep still runs before it (Q11: the parent closes on the next sweep); the catch-up record
is taken after it and covers ``attestations`` and ``targets``, so the hole's record and its
``Proof.lean`` (written into the checkout by ``apply_partial``) are laid again by a catch-up. And
the step's script is run, with ``uv`` stood in by a logger, on an out directory with two hole
records and on one with none, which is what a target pinned before F32 leaves.
"""

from __future__ import annotations

import json
import os
import re
import stat
import subprocess
from pathlib import Path
from typing import Any

import pytest
from test_finding_merge_actor_wakes import load_gate_doc

from opn_gate import config, postmerge

POSTMERGE = "postmerge"
REDERIVE = "Re-derive the verdict on the merge commit"
JOIN = "Join what this merge made provable"
SIGN = "Sign with the gate key (the only step that sees it)"
KEEP = "Keep this merge's own record"
NUMBER = 1234


@pytest.fixture(scope="module")
def gate_doc() -> dict[Any, Any]:
    doc: dict[Any, Any] = load_gate_doc()
    return doc


def steps(doc: dict[Any, Any]) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = doc["jobs"][POSTMERGE]["steps"]
    return found


def index(doc: dict[Any, Any], prefix: str) -> int:
    hits = [i for i, s in enumerate(steps(doc)) if str(s.get("name", "")).startswith(prefix)]
    assert len(hits) == 1, prefix
    return hits[0]


def test_the_key_step_signs_each_hole_record_into_its_path(gate_doc: dict[Any, Any]) -> None:
    run = str(steps(gate_doc)[index(gate_doc, SIGN)]["run"])
    assert "postmerge-out/hole-attestations/" in run, "the key step does not read the hole records"
    # the name postmerge.hole_attestation_path gives: the partial's number, then the hole id
    assert re.search(r'--out "attestations/\$number\.\$hole\.json"', run), run
    assert postmerge.HOLE_ATTESTATIONS_DIR == "hole-attestations"


def test_no_step_before_the_key_step_is_granted_a_secret(gate_doc: dict[Any, Any]) -> None:
    at = index(gate_doc, SIGN)
    before = [s.get("name") for s in steps(gate_doc)[:at] if "secrets." in json.dumps(s)]
    assert before == []
    assert "secrets." not in json.dumps(gate_doc["jobs"][POSTMERGE].get("env") or {})
    readers = [s.get("name") for s in steps(gate_doc) if "OPN_GATE_SIGNING_KEY" in json.dumps(s)]
    assert readers == [SIGN]


def test_the_sweep_stays_before_signing_and_the_record_after(gate_doc: dict[Any, Any]) -> None:
    rederive, join, sign, keep = (index(gate_doc, p) for p in (REDERIVE, JOIN, SIGN, KEEP))
    assert rederive < join < sign < keep  # Q11: the sweep does not see this merge's hole proved


def test_the_catch_up_record_covers_the_hole_proof_and_record(gate_doc: dict[Any, Any]) -> None:
    run = str(steps(gate_doc)[index(gate_doc, KEEP)]["run"])
    added = re.search(r"git add -A -- (?P<paths>[^\n]+)", run)
    assert added is not None, run
    paths = added.group("paths").split()
    # the hole's signed record is under attestations/, its Proof.lean under targets/<t>/nodes/
    assert "attestations" in paths and "targets" in paths
    assert "--binary" in run and "record.patch" in run


# --- the key step's script, run ----------------------------------------------------------------


def sign_script(doc: dict[Any, Any]) -> str:
    s = steps(doc)[index(doc, SIGN)]
    return str(s["run"]).replace("${{ steps.pr.outputs.number }}", str(NUMBER))


def run_sign_step(doc: dict[Any, Any], tmp_path: Path, holes: list[str]) -> tuple[Path, list[str]]:
    """Run the key step's script in a scratch checkout with ``uv`` replaced by a logger that
    writes ``--out`` as a copy of ``--attestation``. Answers the checkout and the logged calls."""
    work = tmp_path / "graph"
    (work / "keys").mkdir(parents=True)
    env = config.child_environment(drop=config.GIT_REPO_VARIABLES)
    subprocess.run(["git", "init", "-q", str(work)], check=True, env=env)
    temp = tmp_path / "runner"
    out = temp / "postmerge-out"
    out.mkdir(parents=True)
    (out / "attestation.json").write_text('{"partial": true}\n', encoding="utf-8")
    if holes:
        (out / "hole-attestations").mkdir()
        for hole in holes:
            (out / "hole-attestations" / f"{hole}.json").write_text(
                json.dumps({"hole": hole}) + "\n", encoding="utf-8"
            )
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log = tmp_path / "uv.log"
    uv = bin_dir / "uv"
    uv.write_text(
        "#!/bin/sh\n"
        f'printf "%s\\n" "$*" >> "{log}"\n'
        'src=""; dst=""\n'
        'while [ $# -gt 0 ]; do case "$1" in\n'
        '  --attestation) src="$2"; shift ;; --out) dst="$2"; shift ;; esac; shift; done\n'
        '[ -n "$dst" ] && mkdir -p "$(dirname "$dst")" && cp "$src" "$dst"\n'
        "exit 0\n",
        encoding="utf-8",
    )
    uv.chmod(uv.stat().st_mode | stat.S_IEXEC)
    env.update(
        PATH=f"{bin_dir}{os.pathsep}{env.get('PATH', '')}",
        RUNNER_TEMP=str(temp),
        NEEDS_GATE="true",
        OPN_GATE_SIGNING_KEY="not-a-key",
    )
    proc = subprocess.run(
        ["bash", "-c", sign_script(doc)], cwd=work, env=env, capture_output=True, text=True,
        check=False,
    )  # fmt: skip
    assert proc.returncode == 0, proc.stdout + proc.stderr
    calls = log.read_text(encoding="utf-8").splitlines() if log.exists() else []
    return work, calls


def test_the_step_signs_the_partial_and_every_hole(
    gate_doc: dict[Any, Any], tmp_path: Path
) -> None:
    holes = ["erdos-68--h1", "erdos-1094--h3@2"]
    work, calls = run_sign_step(gate_doc, tmp_path, holes)
    signed = sorted(p.relative_to(work).as_posix() for p in (work / "attestations").iterdir())
    expected = [
        postmerge.attestation_path(Path(), NUMBER).as_posix(),
        *(postmerge.hole_attestation_path(Path(), NUMBER, h).as_posix() for h in holes),
    ]
    assert signed == sorted(expected)
    for hole in holes:
        body = (work / postmerge.hole_attestation_path(Path(), NUMBER, hole)).read_text()
        assert json.loads(body) == {"hole": hole}
    assert len(calls) == 1 + len(holes)
    assert all("opn_gate.cli sign" in c and "--public-key keys/gate.pub" in c for c in calls)


def test_the_step_is_inert_where_no_hole_record_was_written(
    gate_doc: dict[Any, Any], tmp_path: Path
) -> None:
    """A target pinned before F32 (or a partial carrying no proof) leaves no hole-attestations
    directory: the step signs the merge's record and nothing else."""
    work, calls = run_sign_step(gate_doc, tmp_path, [])
    signed = [p.relative_to(work).as_posix() for p in (work / "attestations").iterdir()]
    assert signed == [postmerge.attestation_path(Path(), NUMBER).as_posix()]
    assert len(calls) == 1
