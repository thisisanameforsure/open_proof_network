"""F15-T13 / AC15: R16's path, end to end over the fixture graph and the fake host, under 10 s.

1. A proposal-shaped target taken in with a signed steward record is claimable under the
   enforced rule, unclaimable after the steward steps down, and claimable either way with the
   rule off; the api's claim answers 201 and then 409 ``no-steward``.
2. A fidelity signer's proof pays like anyone's, and a prover may sign (Q14: no bar).
3. A resolved target moves undigested → explained → written-up as signatures and the write-up
   record land.
4. The merge message names the stewards.
5. The products reproduce byte for byte.
6. The rendered site shows each state.
"""

from __future__ import annotations

import subprocess
import time
from pathlib import Path
from typing import Any

import pytest
import samples
from api_fakes import make_harness
from fixture import COMMIT, MERGE, NOW, build, nodes_dir
from harness import take_in
from test_modes import CURATOR, write_curators

from opn_gate import (
    cli,
    explainers,
    fidelity,
    ledger,
    modes,
    policy,
    postmerge,
    products,
    schemas,
    steward,
    writeup,
)
from opn_gate.paths import Change
from opn_gate.signer import SshKeygenSigner
from opn_site import model, render

GRAPH_URL = "https://github.com/thisisanameforsure/open_proof_network_graph"
PROPOSED, RESOLVED = "proposed-target", "resolved-target"
ROOTS = {PROPOSED: "proposed-lemma", RESOLVED: "resolved-lemma"}
STEWARD, PROVER, SIGNER_ID = "alice-steward", "bob-prover", "carol-signer"
SIGNER = SshKeygenSigner()


def render_products(root: Path) -> None:
    products.generate(root, rendered_from=COMMIT, commit_time=NOW).write(root)


def row_of(root: Path, target_id: str) -> dict[str, Any]:
    import json  # noqa: PLC0415

    rows = json.loads((root / "targets" / "index.json").read_text(encoding="utf-8"))["targets"]
    [row] = [r for r in rows if r["target_id"] == target_id]
    return dict(row)


def stage(root: Path, tmp_path: Path, node_id: str, *, proved: bool) -> Path:
    import shutil  # noqa: PLC0415

    import yaml  # noqa: PLC0415

    staged = tmp_path / node_id
    shutil.copytree(nodes_dir(root) / "and-reassoc", staged)
    meta = yaml.safe_load((staged / "META.yaml").read_text(encoding="utf-8"))
    meta["id"] = node_id
    (staged / "META.yaml").write_text(yaml.safe_dump(meta, sort_keys=False), encoding="utf-8")
    if not proved:
        (staged / "Proof.lean").unlink()
    return staged


@pytest.fixture
def keys(tmp_path: Path) -> dict[str, Path]:
    out: dict[str, Path] = {}
    for who in (STEWARD, CURATOR):
        key = tmp_path / f"{who}.key"
        subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(key)], check=True)
        out[who] = key
    return out


def test_the_whole_life(  # noqa: PLR0915 — one life, walked in order
    tmp_path: Path, keys: dict[str, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    started = time.monotonic()
    root = build(tmp_path / "g")
    write_curators(root, CURATOR)

    # 1. A proposal-shaped target with a signed steward record, under the enforced rule.
    proposal = {"kind": "proposal", "ref": f"{GRAPH_URL}/issues/7", "url": None}
    take_in(
        root, PROPOSED, root_dir=stage(root, tmp_path, ROOTS[PROPOSED], proved=False),
        track="open", source=proposal, proposer=STEWARD, repo_url=GRAPH_URL,
    )  # fmt: skip
    target = root / "targets" / PROPOSED
    steward.write(
        target, action=steward.COMMIT, login=STEWARD, name="Alice", date="2026-09-16",
        link="https://orcid.org/0000-0002-1825-0097", key_path=keys[STEWARD], signer=SIGNER,
    )  # fmt: skip
    policy.write(root, policy.document(enforced=True, since="2026-09-16", evidence="calibration"))
    render_products(root)
    row = row_of(root, PROPOSED)
    assert row["claimable"] is True and [s["login"] for s in row["stewards"]] == [STEWARD]
    assert row["not_claimable"] == []

    h = make_harness()

    def serve() -> None:
        h.githost.files["frontier.json"] = (root / "frontier.json").read_bytes()
        h.githost.files["targets/index.json"] = (root / "targets/index.json").read_bytes()
        h.context.files.clear()

    serve()
    token = h.token_for("code_alice", "alice-p")
    made = h.client.post("/claims", json={"node_id": ROOTS[PROPOSED]}, headers=h.auth(token))
    assert made.status_code == 201, made.text

    steward.write(
        target, action=steward.STEP_DOWN, login=STEWARD, date="2026-09-17",
        key_path=keys[STEWARD], signer=SIGNER,
    )  # fmt: skip
    render_products(root)
    row = row_of(root, PROPOSED)
    assert row["claimable"] is False and row["not_claimable"] == ["no-steward"]
    assert row["stewards"] == []
    serve()
    refused = h.client.post("/claims", json={"node_id": ROOTS[PROPOSED]}, headers=h.auth(token))
    assert refused.status_code == 409 and refused.json()["details"]["not_claimable"] == [
        "no-steward"
    ]

    (root / "policy.json").unlink()  # the rule off: claimable either way
    render_products(root)
    assert row_of(root, PROPOSED)["claimable"] is True
    policy.write(root, policy.document(enforced=True, since="2026-09-16", evidence="calibration"))
    steward.write(
        target, action=steward.COMMIT, login=STEWARD, name="Alice", date="2026-09-18",
        link="https://orcid.org/0000-0002-1825-0097", key_path=keys[STEWARD], signer=SIGNER,
    )  # fmt: skip
    render_products(root)
    assert row_of(root, PROPOSED)["claimable"] is True

    # 2. A fidelity signer's proof pays like anyone's (Q14 rescinded R5's bar), and a prover may
    # sign: D-9's non-author rule is the only exclusion.
    fidelity.attest(
        target, "root", "screened-and-signed", attestor=SIGNER_ID, date="2026-09-16",
        evidence="read the Lean against the English",
    )  # fmt: skip
    proof = Change("A", f"targets/{PROPOSED}/nodes/{ROOTS[PROPOSED]}/Proof.lean")
    earned, skipped, _ = cli._merge_entries(
        root, modes.classify([proof]), identity=SIGNER_ID, commit="a" * 40,
        date="2026-09-16T00:00:00Z", tooling=ledger.UNDECLARED,
        doc={"schema": ledger.SCHEMA, "identity": SIGNER_ID, "entries": []},
    )  # fmt: skip
    assert [e.line for e in earned] == ["proof"] and skipped == []
    ledger.record(root, SIGNER_ID, earned[0])
    assert ledger.holds_proof_line(root, SIGNER_ID, PROPOSED)
    assert not hasattr(fidelity, "prover_bar")

    # 3. A resolved target: undigested → explained → written-up.
    take_in(
        root, RESOLVED, root_dir=stage(root, tmp_path, ROOTS[RESOLVED], proved=True),
        track="formalization",
    )  # fmt: skip
    resolved_node = root / "targets" / RESOLVED / "nodes" / ROOTS[RESOLVED]
    attestation = samples.attestation(
        node_id=ROOTS[RESOLVED], graph_id=RESOLVED,
        statement_hash=schemas.content_hash((resolved_node / "Statement.lean").read_bytes()),
        merge_commit=MERGE, graph_commit=MERGE, runner="hosted",
        review={"kind": "pr-approval", "reviewer": "reviewer-one", "reference": None},
    )  # fmt: skip
    (root / "attestations" / "000900.json").write_bytes(schemas.canonical_json(attestation))
    render_products(root)
    assert row_of(root, RESOLVED)["status"] == "resolved"
    assert row_of(root, RESOLVED)["digestion"]["state"] == "undigested"
    text = "---\nauthor: someone\ndate: 2026-09-16\n---\nWhy it holds.\n"
    digest = schemas.content_hash(text.encode("utf-8"))
    (resolved_node / "explainer" / f"{digest}.md").write_text(text, encoding="utf-8")
    signature = explainers.sign(
        resolved_node, digest, target_id=RESOLVED, signer_login=CURATOR, date="2026-09-16",
        key_path=keys[CURATOR], signer=SIGNER,
    )  # fmt: skip
    change = Change("A", signature.relative_to(root).as_posix())
    assert modes.check(root, modes.classify([change])) == []  # a curator's, accepted
    render_products(root)
    assert row_of(root, RESOLVED)["digestion"]["state"] == "explained"
    writeup.write(
        root / "targets" / RESOLVED, kind="paper", title="The paper", url="https://arxiv.org/abs/1",
        date="2026-09-16", signer_login=CURATOR, key_path=keys[CURATOR], signer=SIGNER,
    )  # fmt: skip
    render_products(root)
    digestion = row_of(root, RESOLVED)["digestion"]
    assert digestion["state"] == "written-up" and digestion["proved_explained"] == 1

    # 4. The merge message names the stewards; 5. the products reproduce byte for byte.
    logins = steward.active_logins(target, SIGNER)
    assert postmerge.bot_commit_message(9, "pass", logins) == f"gate: #9 pass · cc @{STEWARD}"
    assert (
        postmerge.bot_commit_message(
            9, "pass", steward.active_logins(root / "targets" / RESOLVED, SIGNER)
        )
        == "gate: #9 pass"
    )
    first = {
        p: (root / p).read_bytes() for p in ("frontier.json", "targets/index.json", "info.json")
    }
    render_products(root)
    assert first == {p: (root / p).read_bytes() for p in first}

    # 6. The site shows each state.
    pages = render.render_site(model.load_site(root, COMMIT), repo_url="https://github.com/x/g")
    proposed = pages[f"problems/{PROPOSED}/index.html"]  # F04-T12: the problem page
    assert "Alice" in proposed and "committed 2026-09-18" in proposed
    assert "This problem is open for work." in proposed
    resolved = pages[f"problems/{RESOLVED}/index.html"]
    assert "Resolved — <strong>written-up</strong>" in resolved and "The paper" in resolved
    written_up = '<span class="stage on"><span class="dot dot-proved"></span>Written up</span>'
    assert written_up in resolved
    node = pages[f"nodes/{RESOLVED}/{ROOTS[RESOLVED]}/index.html"]
    assert f"Explained and vouched for by <strong>{CURATOR}</strong>" in node
    assert '<span class="big">1 / ' in pages["index.html"]  # explained of proved (D-36 v3.17)
    assert time.monotonic() - started < 10, "the lifecycle test must stay under 10 s (§6)"
