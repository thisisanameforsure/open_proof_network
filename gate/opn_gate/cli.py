"""The gate's command line: one codebase, three invocations (D-4; F00-R11).

    python -m opn_gate.cli pregate --graph <graph-checkout> --node <id> [--sign KEY] ...

``gate/pregate.sh`` wraps ``pregate``. Exit codes: 0 pass · 1 fail · 3 bounced · 2 usage or
internal error before a verdict existed. Every run that reaches the pipeline writes
``verdict.json`` and ``attestation.json`` and prints the verdict summary as JSON on stdout, so an
agent can parse it and self-correct (D-27).
"""

from __future__ import annotations

import argparse
import json
import logging
import subprocess
import sys
import tempfile
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from opn_gate import (
    admit,
    attestation,
    bounce,
    cache,
    config,
    curator,
    defs,
    exhibits,
    fidelity,
    intake,
    layout,
    ledger,
    models,
    modes,
    objectstore,
    paths,
    pipeline,
    postmerge,
    products,
    qa,
    sandbox,
    scaffold,
    schemas,
    signer,
    toolchain,
)
from opn_gate import graph as graphmod
from opn_gate import submission as submissionmod
from opn_gate.paths import Change, Claim
from opn_gate.steps.base import RunContext
from opn_gate.steps.hazards import HazardsStep, StatementStep
from opn_gate.steps.toolchain_step import ToolchainStep

GATE_DIR = Path(__file__).resolve().parents[1]

log = logging.getLogger("opn_gate")

EXIT_PASS = 0
EXIT_FAIL = 1
EXIT_ERROR = 2
EXIT_BOUNCED = 3


class CliError(Exception):
    """A problem with the invocation itself, reported before any verdict exists."""


#: The curator's commands (F08-R9 to R12): what one of them refuses is answered as
#: ``{"ok": false, "refused": ...}`` and exit 1, whichever module raised it.
CURATOR_COMMANDS: frozenset[str] = frozenset(
    {"revise", "consolidate", "status", "missing-library", "intake", "fidelity", "qa"}
)
#: What a curator command refuses on: a record that does not satisfy its schema, a statement the
#: scaffold cannot take, a graph that does not derive. Anywhere else these are exit 2.
_REFUSALS: tuple[type[Exception], ...] = (
    schemas.SchemaError,
    scaffold.ScaffoldError,
    graphmod.GraphError,
    intake.IntakeError,
    fidelity.FidelityError,
    qa.QaError,
)
#: The gate's own error family, plus the OS's for a flag file that cannot be read: an input or
#: environment problem, reported on stderr as exit 2 — never a traceback (conventions §5; F08-Q18).
_ENVIRONMENT_ERRORS: tuple[type[Exception], ...] = (
    *_REFUSALS,
    signer.SignerError,
    sandbox.SandboxError,
    toolchain.ToolchainError,
    toolchain.ToolchainMissingError,
    postmerge.GraphWriteError,
    OSError,
)
DATE_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


def positive_int(text: str) -> int:
    """An argparse type for a count with a lower bound of one (F08-R11: K below 1 makes D-33's
    attempt threshold vacuous)."""
    try:
        value = int(text)
    except ValueError:
        msg = f"{text!r} is not an integer"
        raise argparse.ArgumentTypeError(msg) from None
    if value < 1:
        msg = f"must be at least 1, got {value}"
        raise argparse.ArgumentTypeError(msg)
    return value


def build_parser() -> argparse.ArgumentParser:  # noqa: PLR0915 — one statement per flag
    parser = argparse.ArgumentParser(prog="opn-gate", description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)

    pre = sub.add_parser("pregate", help="run gate steps 1, 2 and 4-8 locally on one node")
    pre.add_argument("--graph", required=True, type=Path, help="path to the graph checkout")
    pre.add_argument("--node", required=True, help="the claimed node id")
    pre.add_argument("--target", help="target id (inferred when the graph has exactly one)")
    pre.add_argument("--base", default=None, help="git ref to diff against (default: HEAD)")
    pre.add_argument("--sign", type=Path, metavar="KEY", help="sign with this SSH private key")
    pre.add_argument("--model", help="model used, as declared (D-23)")
    pre.add_argument("--harness", help="harness used, as declared (D-23)")
    pre.add_argument("--out", type=Path, help="output directory (default: a fresh temp dir)")
    pre.add_argument("--install", action="store_true", help="let elan install the pinned toolchain")
    pre.add_argument("--no-diff", action="store_true", help="skip the diff (bare tree, no git)")

    rep = sub.add_parser("reproduce", help="replay a merged commit inside the step-3 image (D-5)")
    rep.add_argument("--graph", required=True, type=Path, help="path to the graph checkout")
    rep.add_argument("--commit", required=True, help="the commit to reproduce")
    rep.add_argument("--node", required=True, help="the node the commit proved")
    rep.add_argument("--target", help="target id (inferred when the graph has exactly one)")
    rep.add_argument("--compare", type=Path, help="committed attestation to compare against")
    _add_sandbox_args(rep)

    gate = sub.add_parser("gate", help="the authoritative run on a pull request (gate.yml)")
    gate.add_argument("--graph", required=True, type=Path, help="checkout at the PR merge commit")
    gate.add_argument("--base", required=True, help="the pull request's base sha")
    gate.add_argument("--head", default="HEAD", help="the commit to check (default HEAD)")
    gate.add_argument("--target", required=True)
    gate.add_argument("--node", required=True)
    gate.add_argument("--pr-body-file", required=True, type=Path)
    _add_sandbox_args(gate)

    post = sub.add_parser("postmerge", help="re-derive on the merge commit; record step 9")
    post.add_argument("--graph", required=True, type=Path)
    post.add_argument("--commit", required=True, help="the merge commit")
    post.add_argument("--pr", required=True, type=int, help="the merged pull request number")
    post.add_argument(
        "--review-kind",
        required=True,
        choices=["tutorial", "pr-approval", "certificate", "provenance"],
        help="what satisfies step 9 for this node (D-4 v3.11)",
    )
    post.add_argument("--reviewer", help="the approving non-author reviewer (pr-approval)")
    post.add_argument("--review-reference", help="certificate id or registry reference")
    # F07-R6 (F11-T4): a merged partial's holes become child nodes in the checkout, for the
    # bot commit to carry. Asked for explicitly, so the graph's workflow passes it only in
    # partial mode and an older pin, which does not know the flag, is never handed it (F08-Q8).
    post.add_argument(
        "--apply-partial",
        action="store_true",
        help="after a passing partial, create its hole children and file the assembly (F07-R6)",
    )
    post.add_argument(
        "--pr-body-file", type=Path, help="the pull request body: the pseudonym for the children"
    )
    post.add_argument("--author", help="the pull request's author, for a hand-opened one")
    post.add_argument(
        "--approval-body-file",
        type=Path,
        action="append",
        default=[],
        help="an approving review's body; a waived proof needs one naming the waiver (F02-R9)",
    )
    post.add_argument("--target", required=True)
    post.add_argument("--node", required=True)
    _add_sandbox_args(post)

    cls = sub.add_parser("classify", help="what kind of pull request this is (F07-R3)")
    cls.add_argument("--graph", required=True, type=Path, help="checkout at the PR merge commit")
    cls.add_argument("--base", required=True, help="the pull request's base sha")
    cls.add_argument("--head", default="HEAD", help="the commit to classify (default HEAD)")
    cls.add_argument(
        "--author",
        help="the login that opened the pull request; curator mode needs it listed in "
        "curators.json (F08-R8). Default: OPN_PR_AUTHOR from the environment",
    )

    for add_parsers in (
        _add_graph_tool_parsers,
        _add_curator_parsers,
        _add_intake_parsers,
        _add_qa_parsers,
        _add_cache_parsers,
    ):
        add_parsers(sub)

    sign = sub.add_parser("sign", help="sign an attestation with the gate key from the environment")
    sign.add_argument("--attestation", required=True, type=Path)
    sign.add_argument("--public-key", required=True, type=Path, help="keys/gate.pub to verify")
    sign.add_argument("--out", required=True, type=Path)
    return parser


def _add_graph_tool_parsers(sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """The graph-side tools that are not proof runs: admission (F08), exhibits (F08), step 6
    alone (F02) and the products (F03)."""
    exh = sub.add_parser("exhibits", help="elaborate the Lean exhibits an append carries (F08)")
    exh.add_argument("--graph", required=True, type=Path, help="checkout at the PR merge commit")
    exh.add_argument("--base", required=True, help="the pull request's base sha")
    exh.add_argument("--head", default="HEAD", help="the commit to check (default HEAD)")
    exh.add_argument("--out", type=Path, help="work directory (default: a fresh temp dir)")
    exh.add_argument("--install", action="store_true", help="let elan install the pinned toolchain")
    exh.add_argument("--sandbox", action="store_true", help="elaborate inside the step-3 image")
    exh.add_argument("--image", help="sandbox image tag (default: built from gate/Dockerfile)")
    exh.add_argument("--no-build", action="store_true", help="fail if the image is not present")

    adm = sub.add_parser("admit", help="may this node directory enter the graph? (F08-R1)")
    adm.add_argument("node_dir", type=Path, help="targets/<target>/nodes/<id> in a graph checkout")
    adm.add_argument("--out", type=Path, help="work directory (default: a fresh temp dir)")
    adm.add_argument("--install", action="store_true", help="let elan install the pinned toolchain")
    adm.add_argument(
        "--sandbox",
        action="store_true",
        help="elaborate inside the step-3 image, as the authoritative gate must (F08-R2, C9)",
    )
    adm.add_argument("--image", help="sandbox image tag (default: built from gate/Dockerfile)")
    adm.add_argument("--no-build", action="store_true", help="fail if the image is not present")

    haz = sub.add_parser("hazards", help="run step 6 alone on a node directory (F02-R7)")
    haz.add_argument("node_dir", type=Path, help="targets/<target>/nodes/<id> in a graph checkout")
    haz.add_argument("--out", type=Path, help="work directory (default: a fresh temp dir)")
    haz.add_argument("--install", action="store_true", help="let elan install the pinned toolchain")

    prod = sub.add_parser("products", help="regenerate the merge products (F03; D-35)")
    prod.add_argument("--graph", required=True, type=Path, help="path to the graph checkout")
    prod.add_argument("--commit", default="HEAD", help="the commit the products render (git)")
    prod.add_argument("--out", type=Path, help="write here instead of into the checkout")
    prod.add_argument("--no-meta", action="store_true", help="do not rewrite META.yaml status")
    # F11-R6: a Mathlib-pinned target's tag scan runs inside the step-3 image (C9), chosen by
    # the spec like every other sandboxed run (F10-Q10); these two only override that choice.
    prod.add_argument("--image", help="sandbox image tag for the tag scan (default: from the spec)")
    prod.add_argument("--no-build", action="store_true", help="fail if the image is not present")
    prod.add_argument(
        "--claims-url",
        help="the service's GET /claims.json; refreshes claims.json, keeping the committed "
        "snapshot if the service is unreachable (F05-R10)",
    )


def _add_curator_parsers(sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """The curator's commands (F08-R9 to R12) and the post-merge ledger writer (F08-R13)."""

    def common(p: argparse.ArgumentParser) -> None:
        p.add_argument("--graph", required=True, type=Path, help="path to the graph checkout")
        p.add_argument("--target", help="target id (inferred when the graph has exactly one)")
        p.add_argument("--author", required=True, help="the curator's pseudonym, on the record")
        p.add_argument("--date", help="UTC timestamp of the act (default: now)")
        p.add_argument(
            "--branch",
            help="also create this git branch and commit what was written, ready for a curator "
            "pull request (F08-R8)",
        )

    rev = sub.add_parser("revise", help="version a defective statement (F08-R9; D-8)")
    common(rev)
    rev.add_argument("node_id", help="the node whose statement is defective")
    rev.add_argument("--statement", required=True, type=Path, help="the new Statement.lean")
    rev.add_argument("--request", required=True, type=Path, help="the revision request acted on")

    con = sub.add_parser("consolidate", help="mark a duplicate node superseded (F08-R10; D-29)")
    common(con)
    con.add_argument("keep", help="the node that stays")
    con.add_argument("drop", help="the node that is superseded by it")
    con.add_argument("--no-toolchain", action="store_true", help="accept identical hashes only")
    con.add_argument("--out", type=Path, help="work directory (default: a fresh temp dir)")
    con.add_argument("--install", action="store_true", help="let elan install the pinned toolchain")
    con.add_argument("--sandbox", action="store_true", help="elaborate inside the step-3 image")
    con.add_argument("--image", help="sandbox image tag (default: built from gate/Dockerfile)")
    con.add_argument("--no-build", action="store_true", help="fail if the image is not present")

    st = sub.add_parser("status", help="an abandonment or dormancy record (F08-R11; D-14, D-33)")
    common(st)
    st.add_argument("ref", help="a node id (abandoned) or the target id (dormant, active)")
    st.add_argument("status", choices=[*curator.NODE_STATUSES, *curator.TARGET_STATUSES])
    st.add_argument("--cause", required=True, help="the published reasoning (D-33 b)")
    st.add_argument(
        "--k", type=positive_int, default=curator.DEFAULT_K, help="D-33's K in force (at least 1)"
    )
    st.add_argument("--n", type=int, default=curator.DEFAULT_N_DAYS, help="D-33's N (days)")

    ml = sub.add_parser("missing-library", help="the D-13 aggregate for the curator (F08-R12)")
    ml.add_argument("--graph", required=True, type=Path, help="path to the graph checkout")
    ml.add_argument("--target", help="target id (inferred when the graph has exactly one)")
    ml.add_argument("--threshold", type=int, default=curator.DEFAULT_THRESHOLD)

    led = sub.add_parser("ledger", help="the statement line for a merged proposal (F08-R13)")
    led.add_argument("--graph", required=True, type=Path)
    led.add_argument("--commit", required=True, help="the merge commit")


def _add_cache_parsers(sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """The olean cache (F10-R7, R8): ``cache fetch`` for a checkout, ``cache publish`` for the
    post-merge job."""
    top = sub.add_parser("cache", help="the olean cache a graph names in gate-spec.json (F10)")
    ops = top.add_subparsers(dest="cache_command", required=True)
    fetch = ops.add_parser("fetch", help="fetch the newest verified cache at or before a commit")
    fetch.add_argument("--graph", required=True, type=Path, help="path to the graph checkout")
    fetch.add_argument("--target", help="target id (inferred when the graph has exactly one)")
    fetch.add_argument("--commit", default="HEAD", help="the graph commit to key on")
    fetch.add_argument("--out", type=Path, help="where to put it (default: a fresh temp dir)")
    pub = ops.add_parser("publish", help="build the merged tree's oleans, pack, upload (postmerge)")
    pub.add_argument("--graph", required=True, type=Path, help="path to the graph checkout")
    pub.add_argument("--commit", default="HEAD", help="the merge commit the cache is keyed by")
    pub.add_argument("--target", help="target id (inferred when the graph has exactly one)")
    pub.add_argument("--bucket", help="the S3 bucket to upload to (omit: build and pack only)")
    pub.add_argument("--prefix", default="", help="key prefix inside the bucket")
    pub.add_argument("--out", type=Path, help="work directory (default: a fresh temp dir)")
    pub.add_argument("--install", action="store_true", help="let elan install the pinned toolchain")
    pub.add_argument("--sandbox", action="store_true", help="build inside the step-3 image")
    pub.add_argument("--image", help="sandbox image tag (default: from the spec, or built)")
    pub.add_argument("--no-build", action="store_true", help="fail if the image is not present")


def _add_import_parser(acts: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """``intake import-fc`` (F11-R9; D-10): one registry statement, under its own licence."""
    imp = acts.add_parser("import-fc", help="import a Formal Conjectures statement (F11-R9)")
    imp.add_argument("source", type=Path, help="the statement file in a checkout of the registry")
    imp.add_argument("--at", dest="commit", required=True, help="the upstream commit, pinned")
    imp.add_argument("--graph", required=True, type=Path)
    imp.add_argument("--target", dest="target_id", required=True, help="the new target's id")
    imp.add_argument("--from", dest="record", required=True, type=Path, help="the curator's half")
    imp.add_argument("--witness", required=True, type=Path, help="the root's Witness.lean")
    imp.add_argument("--statement", type=Path, help="the statement adapted to D-3's shape")
    imp.add_argument("--path", dest="rel_path", help="the file's path in the upstream repository")
    imp.add_argument("--repo", required=True, help="the upstream repository, e.g. owner/name")
    imp.add_argument("--url", required=True, help="where the file can be read upstream")
    imp.add_argument("--licence", required=True, help="the upstream SPDX identifier")
    imp.add_argument("--attribution", required=True, help="the attribution the licence requires")
    imp.add_argument("--upstream-author", required=True, help="who wrote the statement (D-10)")
    imp.add_argument("--spec", type=Path, help="gate-spec.json to inherit the gate's settings from")
    imp.add_argument("--author", required=True, help="the curator, on every record")
    imp.add_argument("--date", help="UTC timestamp of the act (default: now)")
    imp.add_argument("--branch", help="also commit what was written on this branch")
    imp.add_argument("--no-toolchain", action="store_true", help="skip admission (R2); testing")
    imp.add_argument("--out", type=Path, help="work directory (default: a fresh temp dir)")
    imp.add_argument("--install", action="store_true", help="let elan install the pin")
    imp.add_argument("--sandbox", action="store_true", help="admit inside the step-3 image")
    imp.add_argument("--image", help="sandbox image tag (default: built from gate/Dockerfile)")
    imp.add_argument("--no-build", action="store_true", help="fail if the image is not present")


def _add_intake_parsers(sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """Curated intake and the fidelity ladder (F11-R2, R3, R5; D-6, D-9, D-10)."""
    intk = sub.add_parser("intake", help="curated target intake (F11-R2, R5; D-6)")
    acts = intk.add_subparsers(dest="action", required=True)

    new_t = acts.add_parser("new", help="take a target in: record, spec, root, defs, certificates")
    new_t.add_argument("target_id", help="the new target's id")
    new_t.add_argument("--graph", required=True, type=Path, help="path to the graph checkout")
    new_t.add_argument("--from", dest="record", required=True, type=Path, help="the target.yaml")
    new_t.add_argument("--root", required=True, type=Path, help="the root node directory")
    new_t.add_argument("--defs", type=Path, help="the target's defs/ directory")
    new_t.add_argument(
        "--spec",
        type=Path,
        help="gate-spec.json to take the gate's own settings from (default: the graph's, when "
        "every existing target agrees on one)",
    )
    new_t.add_argument("--author", required=True, help="the curator, on every record")
    new_t.add_argument("--date", help="UTC timestamp of the act (default: now)")
    new_t.add_argument("--branch", help="also commit what was written on this branch")
    new_t.add_argument("--no-toolchain", action="store_true", help="skip admission (R2); testing")
    new_t.add_argument("--out", type=Path, help="work directory (default: a fresh temp dir)")
    new_t.add_argument("--install", action="store_true", help="let elan install the pin")
    new_t.add_argument("--sandbox", action="store_true", help="admit inside the step-3 image")
    new_t.add_argument("--image", help="sandbox image tag (default: built from gate/Dockerfile)")
    new_t.add_argument("--no-build", action="store_true", help="fail if the image is not present")

    post = acts.add_parser("post", help="record the D-10 posting (F11-R5)")
    post.add_argument("target_id")
    post.add_argument("--graph", required=True, type=Path)
    post.add_argument("--venue", required=True, help="where it was posted")
    post.add_argument("--url", required=True, help="the posting's url")
    post.add_argument("--date", help="UTC timestamp of the posting (default: now)")
    post.add_argument("--branch", help="also commit what was written on this branch")

    _add_import_parser(acts)

    act = acts.add_parser("activate", help="flip the target to active, or say what is missing")
    act.add_argument("target_id")
    act.add_argument("--graph", required=True, type=Path)
    act.add_argument("--author", required=True, help="the curator, on the record")
    act.add_argument("--date", help="UTC timestamp of the act (default: now)")
    act.add_argument("--branch", help="also commit what was written on this branch")

    fid = sub.add_parser("fidelity", help="attest a statement's fidelity (F11-R3; D-9 v3.12)")
    fid.add_argument("target_id")
    fid.add_argument("subject", help="`root`, or the name of one definition in defs/")
    fid.add_argument("grade", choices=list(fidelity.GRADES))
    fid.add_argument("--graph", required=True, type=Path)
    fid.add_argument("--by", required=True, dest="by", help="the attestor (not the author, D-9)")
    fid.add_argument("--evidence", required=True, type=Path, help="a file holding what was checked")
    fid.add_argument("--subject-author", help="required only for a subject with no certificate yet")
    fid.add_argument("--date", help="UTC timestamp of the act (default: now)")
    fid.add_argument("--branch", help="also commit what was written on this branch")


def _add_qa_parsers(sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """F12: the statement-QA pass, one command per layer of D-9 v3.12's pass."""
    top = sub.add_parser("qa", help="the statement-QA pass over a subject (F12; D-9 v3.12)")
    acts = top.add_subparsers(dest="action", required=True)

    def common(p: argparse.ArgumentParser) -> None:
        p.add_argument("target_id")
        p.add_argument("subject", help="`root`, or the name of one definition in defs/")
        p.add_argument("--graph", required=True, type=Path)
        p.add_argument("--date", help="UTC timestamp of the run (default: now)")
        p.add_argument("--branch", help="also commit what was written on this branch")

    scr = acts.add_parser("screen", help="the soundness screens on the root statement (F12-R3)")
    common(scr)
    scr.add_argument("--out", type=Path, help="work directory (default: a fresh temp dir)")
    scr.add_argument("--install", action="store_true", help="let elan install the pinned toolchain")
    scr.add_argument(
        "--sandbox",
        action="store_true",
        help="elaborate inside the step-3 image, as the authoritative run must (F12 §7, C9)",
    )
    scr.add_argument("--image", help="sandbox image tag (default: from the spec)")
    scr.add_argument("--no-build", action="store_true", help="fail if the image is not present")
    scr.add_argument(
        "--by", default=qa.SCREEN_CONTRIBUTOR, help="the contributor a finding's claim names"
    )

    brf = acts.add_parser("brief", help="the grounded review brief (F12-R6): a judgement")
    common(brf)
    brf.add_argument("--out", type=Path, help="work directory (default: a fresh temp dir)")
    brf.add_argument("--install", action="store_true", help="let elan install the pinned toolchain")
    brf.add_argument("--sandbox", action="store_true", help="elaborate inside the step-3 image")
    brf.add_argument("--image", help="sandbox image tag (default: from the spec)")
    brf.add_argument("--no-build", action="store_true", help="fail if the image is not present")

    bt = acts.add_parser("backtranslate", help="English from the Lean alone (F12-R7)")
    common(bt)

    eq = acts.add_parser("equivalence", help="both implications between two nodes (F12-R8)")
    common(eq)
    eq.add_argument("other", help="the node that formalizes the same statement independently")
    eq.add_argument("--out", type=Path, help="work directory (default: a fresh temp dir)")
    eq.add_argument("--install", action="store_true", help="let elan install the pinned toolchain")
    eq.add_argument("--sandbox", action="store_true", help="elaborate inside the step-3 image")
    eq.add_argument("--image", help="sandbox image tag (default: from the spec)")
    eq.add_argument("--no-build", action="store_true", help="fail if the image is not present")

    rte = acts.add_parser("route", help="route a positive screen's claim (F12-R4; D-9 v3.12)")
    common(rte)
    rte.add_argument("claim", help="the file name of the screen-finding claim under defects/")
    rte.add_argument("--reading", required=True, choices=list(qa.READINGS))
    rte.add_argument(
        "--class",
        dest="defect_class",
        required=True,
        help="the D-16 class for a misformalization, or the class that best fits the exhibit",
    )
    rte.add_argument("--by", required=True, dest="by", help="the curator routing it")
    rte.add_argument("--note", help="why, in a sentence")


def _add_sandbox_args(p: argparse.ArgumentParser) -> None:
    """The flags every sandboxed run shares (reproduce, gate, postmerge)."""
    p.add_argument("--out", type=Path, help="output directory (default: a fresh temp dir)")
    p.add_argument("--image", help="sandbox image tag (default: built from gate/Dockerfile)")
    p.add_argument("--no-build", action="store_true", help="fail if the image is not present")


def main(argv: Sequence[str] | None = None) -> int:
    """Every command, behind the one boundary where the gate's errors become exit codes: a
    ``CliError`` or any input/environment error is exit 2 on stderr; a curator command's refusal
    is ``{"ok": false, "refused": ...}`` and exit 1 (conventions §5)."""
    args = build_parser().parse_args(argv)
    try:
        settings = config.load()
    except config.ConfigError as exc:
        return _usage_error(exc)
    logging.basicConfig(level=settings.log_level, format="%(levelname)s %(name)s: %(message)s")
    commands = {
        "pregate": run_pregate,
        "reproduce": run_reproduce,
        "gate": run_gate,
        "classify": run_classify,
        "exhibits": run_exhibits,
        "revise": run_revise,
        "consolidate": run_consolidate,
        "status": run_status,
        "missing-library": run_missing_library,
        "ledger": run_ledger,
        "intake": run_intake,
        "qa": run_qa,
        "fidelity": run_fidelity,
        "postmerge": run_postmerge,
        "admit": run_admit,
        "hazards": run_hazards,
        "products": run_products,
        "sign": run_sign,
        "cache": run_cache,
    }
    try:
        return commands[args.command](args, settings)
    except CliError as exc:
        return _usage_error(exc)
    except curator.CuratorError as exc:  # a refusal, with the reason: nothing was written
        return _refused(exc)
    except _REFUSALS as exc:
        return _refused(exc) if args.command in CURATOR_COMMANDS else _usage_error(exc)
    except _ENVIRONMENT_ERRORS as exc:
        return _usage_error(exc)


def _usage_error(exc: Exception) -> int:
    sys.stderr.write(f"opn-gate: {exc}\n")
    return EXIT_ERROR


def _refused(exc: Exception) -> int:
    sys.stdout.write(json.dumps({"ok": False, "refused": str(exc)}, indent=2) + "\n")
    sys.stderr.write(f"opn-gate: refused: {exc}\n")
    return EXIT_FAIL


def _read_flag_file(path: Path, flag: str) -> str:
    """The text a flag names — read before any expensive work, so a wrong path is a usage
    error and not a traceback after the export, the image build and the run (F08-Q18)."""
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        msg = f"cannot read {flag} {path}: {exc.strerror or exc}"
        raise CliError(msg) from exc


# --- pregate ------------------------------------------------------------------------------------


def run_pregate(args: argparse.Namespace, settings: config.Settings) -> int:
    graph: Path = args.graph.resolve()
    if not graph.is_dir():
        msg = f"graph checkout not found: {graph}"
        raise CliError(msg)
    target_id = args.target or infer_target(graph)
    claim = Claim(target_id, args.node)
    spec_path = layout.gate_spec_path(graph, target_id)
    try:
        spec = schemas.load_json(spec_path, "gate-spec/v1")
    except schemas.SchemaError as exc:
        msg = f"cannot load {spec_path}: {exc}"
        raise CliError(msg) from exc
    try:
        tc = toolchain.LocalToolchain.from_settings(settings)
    except toolchain.ToolchainMissingError as exc:
        raise CliError(str(exc)) from exc
    if args.sign is not None and not args.sign.is_file():
        msg = f"--sign {args.sign} is not a file"
        raise CliError(msg)

    changes: list[Change] | None = None if args.no_diff else worktree_changes(graph, args.base)
    out_dir: Path = (args.out or Path(tempfile.mkdtemp(prefix="opn-pregate-"))).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    ctx = RunContext(
        graph_root=graph,
        claim=claim,
        spec=spec,
        gate_spec_hash=schemas.content_hash(spec_path.read_bytes()),
        changes=changes,
        workdir=out_dir / "work",
        toolchain=tc,
        settings=settings,
        install_toolchain=bool(args.install),
    )
    fetched = attach_cache(ctx, graph, head_commit(graph), out_dir)
    verdict = pipeline.run_submission(ctx)
    doc = attestation.build(
        ctx,
        verdict,
        graph_commit=None if args.no_diff else clean_head(graph),
        tooling={"model": args.model, "harness": args.harness},
    )
    if args.sign is not None:
        try:
            sig = signer.SshKeygenSigner().sign(
                attestation.signed_bytes(doc), args.sign, "contributor"
            )
        except signer.SignerError as exc:
            msg = f"cannot sign with {args.sign}: {exc}"
            raise CliError(msg) from exc
        doc["signature"] = {
            "kind": sig.kind,
            "key_id": sig.key_id,
            "value": sig.value,
            "timestamp": doc["signature"]["timestamp"],
        }
        schemas.validate(doc, attestation.SCHEMA)
    return emit(verdict, doc, out_dir, settings, olean_cache=cache_report(ctx, fetched))


def head_commit(graph: Path) -> str | None:
    """HEAD's sha whether or not the tree is dirty (the cache is keyed by ancestry, F10-R7);
    ``None`` for a bare tree."""
    if _git(graph, "rev-parse", "--is-inside-work-tree").returncode != 0:
        return None
    head = _git(graph, "rev-parse", "HEAD")
    return head.stdout.strip() if head.returncode == 0 and head.stdout.strip() else None


def attach_cache(
    ctx: RunContext, git_root: Path, commit: str | None, out_dir: Path
) -> cache.FetchResult:
    """F10-R7: fetch the newest olean cache at or before ``commit`` into the run's directory and
    hand it to the build step; a miss, a corrupt archive or an unreachable store means the run
    builds everything itself (C7) and says so in the summary."""
    result = cache.prepare(ctx.spec, git_root, commit, out_dir / "olean-cache")
    ctx.data["olean_cache_usage"] = cache.Usage(commit=result.commit)
    if result.fetched is not None:
        ctx.data["olean_cache"] = result.fetched
    return result


def cache_report(ctx: RunContext, fetched: cache.FetchResult) -> dict[str, Any]:
    usage: cache.Usage | None = ctx.data.get("olean_cache_usage")
    report = fetched.as_dict()
    report.update(usage.as_dict() if usage is not None else {"hits": [], "misses": []})
    return report


def emit(
    verdict: pipeline.Verdict,
    doc: dict[str, Any],
    out_dir: Path,
    settings: config.Settings,
    *,
    olean_cache: dict[str, Any] | None = None,
) -> int:
    """Write the verdict and the attestation, print the summary. The cache report rides in the
    summary and ``cache.json`` only: the attestation is a function of the tree and the pinned
    tooling alone (D-5), and whether a dependency's olean was compiled or fetched is not."""
    verdict_doc = verdict.as_dict(settings.diagnostic_max_bytes)
    (out_dir / "verdict.json").write_bytes(schemas.canonical_json(verdict_doc))
    (out_dir / "attestation.json").write_bytes(schemas.canonical_json(doc))
    summary = dict(verdict_doc)
    summary["attestation"] = str(out_dir / "attestation.json")
    summary["verdict_file"] = str(out_dir / "verdict.json")
    if olean_cache is not None:
        (out_dir / "cache.json").write_bytes(schemas.canonical_json(olean_cache))
        summary["olean_cache"] = olean_cache
    sys.stdout.write(json.dumps(summary, indent=2, ensure_ascii=False) + "\n")
    if verdict.verdict == "pass":
        return EXIT_PASS
    if verdict.verdict == "bounced":
        return EXIT_BOUNCED
    return EXIT_FAIL


# --- reproduce ----------------------------------------------------------------------------------


def run_reproduce(args: argparse.Namespace, settings: config.Settings) -> int:
    graph, commit = _checkout_and_commit(args.graph, args.commit)
    committed: dict[str, Any] | None = None
    if args.compare is not None:  # read before the run, so a wrong path costs no sandbox
        try:
            committed = schemas.load_json(args.compare)
        except schemas.SchemaError as exc:
            msg = f"cannot load --compare {args.compare}: {exc}"
            raise CliError(msg) from exc
    out_dir = _out_dir(args.out, "opn-reproduce-")
    ctx = _sandboxed_context(
        graph,
        commit,
        out_dir,
        target=args.target,
        node=args.node,
        settings=settings,
        image=args.image,
        no_build=args.no_build,
    )
    verdict = pipeline.run_submission(ctx)
    doc = attestation.build(ctx, verdict, graph_commit=commit)
    code = emit(verdict, doc, out_dir, settings)
    if committed is not None:
        differing = attestation.compare(committed, attestation.with_step9(doc, committed))
        result = {"identical": not differing, "differing_fields": differing}
        sys.stdout.write(json.dumps(result) + "\n")
        return EXIT_PASS if not differing else EXIT_FAIL
    return code


def run_gate(args: argparse.Namespace, settings: config.Settings) -> int:
    """The authoritative run: bounce rule, then steps 1, 2 and 4-8 in the sandbox (hosted)."""
    graph, head = _checkout_and_commit(args.graph, args.head)
    base = _git(graph, "rev-parse", "--verify", f"{args.base}^{{commit}}").stdout.strip()
    if not base:
        msg = f"unknown base {args.base!r}"
        raise CliError(msg)
    pr_body = _read_flag_file(args.pr_body_file, "--pr-body-file")
    out_dir = _out_dir(args.out, "opn-gate-")
    ctx = _sandboxed_context(
        graph,
        head,
        out_dir,
        target=args.target,
        node=args.node,
        settings=settings,
        image=args.image,
        no_build=args.no_build,
    )
    diff = _git(graph, "diff", "--name-status", "--no-renames", base, head)
    ctx.changes = paths.changes_from_name_status(diff.stdout)
    node_dir = layout.graph_nodes_dir(ctx.graph_root, args.target) / args.node
    statement = node_dir / "Statement.lean"
    policy = bounce.PrecheckPolicy(
        pr_body=pr_body,
        accepted_signatures=tuple(ctx.spec["accepted_precheck_signatures"]),
        max_age_s=int(ctx.spec["precheck_max_age_s"]),
        now=attestation.utc_now(),
        node_id=args.node,
        statement_hash=schemas.content_hash(statement.read_bytes()) if statement.is_file() else "",
    )
    fetched = attach_cache(ctx, graph, head, out_dir)
    verdict = pipeline.run_submission(ctx, precheck=policy)
    doc = attestation.build(ctx, verdict, graph_commit=head)
    return emit(verdict, doc, out_dir, settings, olean_cache=cache_report(ctx, fetched))


def run_classify(args: argparse.Namespace, settings: config.Settings) -> int:
    """F07-R3: what kind of pull request this is, and — for the kinds that build nothing — the
    whole of their checking (R9, R10).

    The workflow runs this before it decides whether to spend a sandbox on the diff: an append or
    an explainer is finished here, a proof or a partial goes on to ``gate``. Exit 0 means the
    classification stands and every check that applies to it passed; 1 means it is refused, with
    every reason in ``problems``.
    """
    graph, head = _checkout_and_commit(args.graph, args.head)
    base = _git(graph, "rev-parse", "--verify", f"{args.base}^{{commit}}").stdout.strip()
    if not base:
        msg = f"unknown base {args.base!r}"
        raise CliError(msg)
    diff = _git(graph, "diff", "--name-status", "--no-renames", base, head)
    try:
        curators = modes.load_curators(graph)
    except modes.CuratorsError as exc:
        raise CliError(str(exc)) from exc
    classification = modes.classify(
        paths.changes_from_name_status(diff.stdout),
        author=args.author or settings.pr_author,
        curators=curators,
    )
    problems = list(classification.problems)
    if classification.ok:
        problems.extend(modes.check(graph, classification, base=base_reader(graph, base)))
    summary = classification.as_dict()
    summary["problems"] = [d.as_dict(settings.diagnostic_max_bytes) for d in problems]
    summary["ok"] = classification.ok and not problems
    # F08-R6, R7: an append that carries a Lean exhibit still needs the sandbox, for that alone.
    carrying = modes.exhibits(graph, classification) if classification.ok else []
    summary["exhibits"] = [loc.path for loc in carrying]
    summary["needs_exhibits"] = bool(carrying)
    sys.stdout.write(json.dumps(summary, indent=2, ensure_ascii=False) + "\n")
    if not summary["ok"]:
        for d in problems:
            sys.stderr.write(f"opn-gate: {d.code}: {d.message}\n")
    return EXIT_PASS if summary["ok"] else EXIT_FAIL


def run_exhibits(args: argparse.Namespace, settings: config.Settings) -> int:
    """F08-R6, R7: elaborate every exhibit the pull request's appended records carry.

    Contributor Lean, so ``--sandbox`` on the authoritative gate (C9). Exit 0 when every exhibit
    elaborates, 1 when one does not, naming it; a diff that is not an append is a usage error,
    because this command is the append mode's build and nothing else's.
    """
    graph, head = _checkout_and_commit(args.graph, args.head)
    base = _git(graph, "rev-parse", "--verify", f"{args.base}^{{commit}}").stdout.strip()
    if not base:
        msg = f"unknown base {args.base!r}"
        raise CliError(msg)
    diff = _git(graph, "diff", "--name-status", "--no-renames", base, head)
    classification = modes.classify(paths.changes_from_name_status(diff.stdout))
    if classification.mode != "append" or classification.target_id is None:
        msg = f"exhibits belong to append mode; this diff is {classification.mode!r}"
        raise CliError(msg)
    records = modes.exhibits(graph, classification)
    out_dir = _out_dir(args.out, "opn-exhibits-")
    workdir = out_dir / "work"
    spec_path = layout.gate_spec_path(graph, classification.target_id)
    try:
        spec = schemas.load_json(spec_path, "gate-spec/v1")
    except schemas.SchemaError as exc:
        msg = f"cannot load {spec_path}: {exc}"
        raise CliError(msg) from exc
    tc: toolchain.Toolchain
    if args.sandbox:
        tag = args.image or ensure_image(spec, build=not args.no_build)
        tc = sandbox.SandboxToolchain(tag, sandbox.Caps.from_spec(spec), read_write=[workdir])
    else:
        try:
            tc = toolchain.LocalToolchain.from_settings(settings)
        except toolchain.ToolchainMissingError as exc:
            raise CliError(str(exc)) from exc
    ctx = RunContext(
        graph_root=graph,
        claim=Claim(classification.target_id, classification.node_id or ""),
        spec=spec,
        gate_spec_hash=schemas.content_hash(spec_path.read_bytes()),
        changes=None,
        workdir=workdir,
        toolchain=tc,
        settings=settings,
        install_toolchain=bool(args.install) and not args.sandbox,
    )
    problems = exhibits.run(ctx, records)
    summary = {
        "ok": not problems,
        "exhibits": [loc.path for loc in records],
        "sandboxed": bool(args.sandbox),
        "problems": [d.as_dict(settings.diagnostic_max_bytes) for d in problems],
    }
    (out_dir / "exhibits.json").write_bytes(schemas.canonical_json(summary))
    sys.stdout.write(json.dumps(summary, indent=2, ensure_ascii=False) + "\n")
    for d in problems:
        sys.stderr.write(f"opn-gate: {d.code}: {d.message}\n")
    return EXIT_PASS if not problems else EXIT_FAIL


def library_scanner(
    graph: Path, out_dir: Path | None, args: argparse.Namespace, settings: config.Settings
) -> products.Scanner | None:
    """F03-R6 on a Mathlib-pinned graph (F11-R6): the statement scan that reads a node's Mathlib
    constants runs *inside the step-3 image*, because a statement elaborates arbitrary code
    (C9) — and it runs there whether or not anyone asked, since there is no legitimate
    host-side choice to offer. A graph with no Mathlib pin has no library tags to scan for and
    gets no scanner, exactly as before, so the tutorial graph's post-merge job is untouched.
    """
    pinned = [
        (t, spec)
        for t in products.target_ids(graph)
        for spec in [schemas.load_json(layout.gate_spec_path(graph, t), "gate-spec/v1")]
        if spec["mathlib_sha"] is not None
    ]
    if not pinned:
        return None
    work_root = (out_dir or Path(tempfile.mkdtemp(prefix="opn-products-"))) / "scan"
    toolchains: dict[str, tuple[sandbox.SandboxToolchain, toolchain.ResolvedToolchain]] = {}

    def scan(node: graphmod.NodeFacts) -> list[str]:
        if node.target_id not in toolchains:
            spec = dict(pinned)[node.target_id]
            tag = getattr(args, "image", None) or ensure_image(
                spec, build=not getattr(args, "no_build", False)
            )
            workdir = work_root / node.target_id
            tc = sandbox.SandboxToolchain(
                tag,
                sandbox.Caps.from_spec(spec),
                read_only=[layout.gate_spec_path(graph, node.target_id).parent],
                read_write=[workdir],
            )
            resolved = tc.resolve(str(spec["lean_toolchain"]), mathlib_sha=str(spec["mathlib_sha"]))
            problem = defs.compile_all(
                tc,
                resolved,
                layout.gate_spec_path(graph, node.target_id).parent,
                workdir,
                timeout_s=float(spec["step3_caps"]["wallclock_s"]),
            )
            if problem is not None:
                raise graphmod.GraphError(f"{node.target_id}: {problem.message}")
            toolchains[node.target_id] = (tc, resolved)
        tc, resolved = toolchains[node.target_id]
        return products.scan_statement(tc, resolved, node, work_root / node.target_id)

    return scan


def run_postmerge(args: argparse.Namespace, settings: config.Settings) -> int:
    """Re-derive on the merge commit and record step 9; signing is the separate `sign` step."""
    graph, commit = _checkout_and_commit(args.graph, args.commit)
    # The flags are checked before the sandbox is spent on the run (F08-Q18).
    try:
        review = postmerge.review_block(
            args.review_kind, reviewer=args.reviewer, reference=args.review_reference
        )
    except ValueError as exc:
        raise CliError(str(exc)) from exc
    bodies = [_read_flag_file(p, "--approval-body-file") for p in args.approval_body_file]
    out_dir = _out_dir(args.out, "opn-postmerge-")
    ctx = _sandboxed_context(
        graph,
        commit,
        out_dir,
        target=args.target,
        node=args.node,
        settings=settings,
        image=args.image,
        no_build=args.no_build,
    )
    verdict = pipeline.run_submission(ctx)
    doc = attestation.build(ctx, verdict, graph_commit=commit)
    doc = postmerge.record_step9(doc, merge_commit=commit, review=review)
    refusal = postmerge.check_waiver(doc, bodies)
    if refusal is not None:  # F02-R9: refuse to attest; nothing is written
        sys.stdout.write(json.dumps({"verdict": "refused", "diagnostic": refusal.as_dict()}) + "\n")
        sys.stderr.write(f"opn-gate: {refusal.message}\n")
        return EXIT_FAIL
    code = emit(verdict, doc, out_dir, settings)
    if code != EXIT_PASS:
        sys.stderr.write("opn-gate: the merged commit does not pass the gate; not attesting\n")
        return code
    if args.apply_partial:
        applied = apply_merged_partial(ctx, verdict, graph, commit, args)
        if applied is not None:
            sys.stdout.write(json.dumps({"partial": applied.as_dict()}) + "\n")
    return code


def apply_merged_partial(
    ctx: RunContext,
    verdict: pipeline.Verdict,
    graph: Path,
    commit: str,
    args: argparse.Namespace,
) -> postmerge.PartialMerge | None:
    """F07-R6, dispatched (F11-T4): the children of a partial that just re-derived as passing,
    written into the *checkout* (the export the run used is a copy), and the assembly filed
    under ``attempts/`` as the record of who decomposed what.

    The pseudonym is the submission block's, from the pull request body (F07-R2, R13); a
    hand-opened pull request has no block and the login the workflow passes stands in. The
    stamp is the merge commit's time, so two merges of one node file distinct attempts.
    """
    partial = verdict.data.get("partial")
    artifact_doc = verdict.data.get("artifact") or {}
    if not isinstance(partial, dict) or artifact_doc.get("kind") not in ("partial", "reduction"):
        sys.stderr.write("opn-gate: --apply-partial given, but the merge was not a partial\n")
        return None
    from opn_gate.steps import artifact as artifactmod  # noqa: PLC0415 — steps.base would cycle

    holes = [artifactmod.Hole.of(h) for h in artifact_doc.get("holes") or []]
    node_dir = layout.graph_nodes_dir(graph, ctx.claim.target_id) / ctx.claim.node_id
    assembly = node_dir / str(partial["path"])
    if not assembly.is_file():
        msg = f"the merged assembly {assembly} is not in the checkout"
        raise CliError(msg)
    body = _read_flag_file(args.pr_body_file, "--pr-body-file") if args.pr_body_file else ""
    pseudonym = attestation.submitter_of(submissionmod.extract(body)) or args.author
    if not pseudonym:
        msg = "--apply-partial needs the pull request body (--pr-body-file) or --author"
        raise CliError(msg)
    when = graphmod.commit_timestamp(graph, commit)
    stamp = when.replace("-", "").replace(":", "")
    try:
        return postmerge.apply_partial(
            node_dir,
            holes,
            partial_text=assembly.read_text(encoding="utf-8"),
            pseudonym=str(pseudonym),
            stamp=stamp,
            author=args.author,
        )
    except postmerge.GraphWriteError as exc:
        raise CliError(str(exc)) from exc


def run_admit(args: argparse.Namespace, settings: config.Settings) -> int:
    """F08-R1: the mechanical admission check over one node directory.

    Prints the verdict JSON — every check, in order, with the first failure named — and exits 0
    when the node may enter the graph, 1 when it may not. No attestation: admission decides
    whether a *statement* is well formed, which is not a claim about mathematics (D-29).
    """
    ctx = node_context(args, settings, prefix="opn-admit-", sandboxed=bool(args.sandbox))
    result = admit.run(ctx)
    summary = result.as_dict(settings.diagnostic_max_bytes)
    summary["node"] = ctx.claim.node_id
    summary["target"] = ctx.claim.target_id
    summary["sandboxed"] = bool(args.sandbox)
    for key in ("hazards", "relation", "relation_label", "statement_axioms", "witness"):
        if key in ctx.data:
            summary[key] = ctx.data[key]
    (ctx.workdir.parent / "admission.json").write_bytes(schemas.canonical_json(summary))
    sys.stdout.write(json.dumps(summary, indent=2, ensure_ascii=False) + "\n")
    if not result.admitted and result.diagnostic is not None:
        sys.stderr.write(
            f"opn-gate: admission failed at {result.first_failing_check}: "
            f"{result.diagnostic.message}\n"
        )
    return EXIT_PASS if result.admitted else EXIT_FAIL


def node_context(
    args: argparse.Namespace, settings: config.Settings, *, prefix: str, sandboxed: bool = False
) -> RunContext:
    """A RunContext over one node directory in a graph checkout — no diff, no Proof.lean.

    ``sandboxed`` puts the toolchain inside the step-3 image with the same mounts the
    authoritative gate uses (F00-R5): the node read-only, the work directory read-write.
    """
    node_dir: Path = args.node_dir.resolve()
    parts = node_dir.parts
    if not node_dir.is_dir() or len(parts) < 4 or parts[-2] != "nodes" or parts[-4] != "targets":
        msg = f"{node_dir} is not a node directory (targets/<target>/nodes/<id>)"
        raise CliError(msg)
    graph = node_dir.parents[3]
    target_id = node_dir.parents[1].name
    spec_path = layout.gate_spec_path(graph, target_id)
    try:
        spec = schemas.load_json(spec_path, "gate-spec/v1")
    except schemas.SchemaError as exc:
        msg = f"cannot load {spec_path}: {exc}"
        raise CliError(msg) from exc
    out_dir = _out_dir(args.out, prefix)
    workdir = out_dir / "work"
    tc: toolchain.Toolchain
    if sandboxed:
        tag = getattr(args, "image", None) or ensure_image(
            spec, build=not getattr(args, "no_build", False)
        )
        tc = sandbox.SandboxToolchain(
            tag, sandbox.Caps.from_spec(spec), read_only=[node_dir], read_write=[workdir]
        )
    else:
        try:
            tc = toolchain.LocalToolchain.from_settings(settings)
        except toolchain.ToolchainMissingError as exc:
            raise CliError(str(exc)) from exc
    return RunContext(
        graph_root=graph,
        claim=Claim(target_id, node_dir.name),
        spec=spec,
        gate_spec_hash=schemas.content_hash(spec_path.read_bytes()),
        changes=None,
        workdir=workdir,
        toolchain=tc,
        settings=settings,
        install_toolchain=bool(args.install) and not sandboxed,
    )


def base_reader(graph: Path, base: str) -> modes.BaseReader:
    """What a path held at ``base`` (``git show``), or ``None`` when it did not exist there."""

    def read(path: str) -> bytes | None:
        proc = subprocess.run(
            ["git", "-C", str(graph), "show", f"{base}:{path}"],
            capture_output=True,
            check=False,
            env=git_environment(),
        )
        return proc.stdout if proc.returncode == 0 else None

    return read


def run_hazards(args: argparse.Namespace, settings: config.Settings) -> int:
    """F02-R7: step 6 alone over a node directory, for admission (F08) and proposers.

    Prints the verdict JSON plus a ``hazards`` block (findings, acknowledgments used); exits 0
    on pass, 1 on fail. No attestation: this is not a submission.
    """
    ctx = node_context(args, settings, prefix="opn-hazards-")
    verdict = pipeline.run_steps(ctx, steps=[ToolchainStep(), StatementStep(), HazardsStep()])
    summary = verdict.as_dict(settings.diagnostic_max_bytes)
    summary["hazards"] = ctx.data.get("hazards")
    sys.stdout.write(json.dumps(summary, indent=2, ensure_ascii=False) + "\n")
    return EXIT_PASS if verdict.ok else EXIT_FAIL


def run_products(args: argparse.Namespace, settings: config.Settings) -> int:
    """F03: regenerate frontier.json, info.json, targets/index.json and every graph.json.

    Renders the checkout as it is, stamped with ``--commit`` (its committer time feeds
    ``ready_since``, R8). A defective graph (cycle, missing dep, ambiguous root) writes nothing
    and exits 1 with the problem named (R3). Library tags on a Mathlib-pinned graph need a scan
    inside the sandbox, which F10 wires; until then such a graph is refused here.
    """
    graph, commit = _checkout_and_commit(args.graph, args.commit)
    out_dir = args.out.resolve() if args.out is not None else graph
    claims_note = postmerge.refresh_claims(graph, getattr(args, "claims_url", None))
    scanner = library_scanner(graph, out_dir if args.out is not None else None, args, settings)
    try:
        products_ = products.generate(
            graph,
            rendered_from=commit,
            commit_time=graphmod.commit_timestamp(graph, commit),
            scanner=scanner,
        )
    except (graphmod.GraphError, schemas.SchemaError) as exc:
        sys.stdout.write(json.dumps({"ok": False, "error": str(exc)}) + "\n")
        sys.stderr.write(f"opn-gate: products not written: {exc}\n")
        return EXIT_FAIL
    written = products_.write(out_dir, write_meta=not args.no_meta and out_dir == graph)
    summary: dict[str, Any] = {
        "ok": True,
        "rendered_from": commit,
        "claims": claims_note or "refreshed",
        "written": [p.as_posix() for p in written],
        "files": sorted(p.as_posix() for p in products_.files),
    }
    sys.stdout.write(json.dumps(summary, indent=2) + "\n")
    return EXIT_PASS


def run_cache(args: argparse.Namespace, settings: config.Settings) -> int:
    return (
        run_cache_fetch(args)
        if args.cache_command == "fetch"
        else run_cache_publish(args, settings)
    )


def _spec_for(graph: Path, target_id: str) -> dict[str, Any]:
    spec_path = layout.gate_spec_path(graph, target_id)
    try:
        return schemas.load_json(spec_path, "gate-spec/v1")
    except schemas.SchemaError as exc:
        msg = f"cannot load {spec_path}: {exc}"
        raise CliError(msg) from exc


def run_cache_fetch(args: argparse.Namespace) -> int:
    """F10-R7 for the devcontainer and anyone else: fetch, verify, report. Exit 0 on a hit,
    1 otherwise — a miss is an answer, not an error."""
    graph = args.graph.resolve()
    if not graph.is_dir():
        msg = f"graph checkout not found: {graph}"
        raise CliError(msg)
    target_id = args.target or infer_target(graph)
    spec = _spec_for(graph, target_id)
    commit = args.commit
    if _git(graph, "rev-parse", "--is-inside-work-tree").returncode == 0:
        resolved = _git(graph, "rev-parse", "--verify", f"{commit}^{{commit}}").stdout.strip()
        commit = resolved or commit
    out_dir = _out_dir(args.out, "opn-cache-")
    result = cache.prepare(spec, graph, commit, out_dir / "olean-cache")
    doc = result.as_dict()
    doc["target"] = target_id
    doc["directory"] = str(out_dir / "olean-cache") if result.fetched else None
    sys.stdout.write(json.dumps(doc, indent=2) + "\n")
    return EXIT_PASS if result.status == "hit" else EXIT_FAIL


def run_cache_publish(args: argparse.Namespace, settings: config.Settings) -> int:
    """F10-R7, R8: the post-merge job's half — build every proved node's oleans from the merged
    tree (inside the image with ``--sandbox``, as the gate builds), pack them with a SHA-256
    manifest, and upload keyed by the merge commit. Without ``--bucket`` it stops after packing,
    which is how a laptop checks what a run would upload."""
    graph, commit = _checkout_and_commit(args.graph, args.commit)
    out_dir = _out_dir(args.out, "opn-cache-publish-")
    tree = export_tree(graph, commit, out_dir / "tree")
    target_id = args.target or infer_target(tree)
    spec = _spec_for(tree, target_id)
    workdir = out_dir / "work"
    tc: toolchain.Toolchain
    if args.sandbox:
        tag = args.image or ensure_image(spec, build=not args.no_build)
        tc = sandbox.SandboxToolchain(tag, sandbox.Caps.from_spec(spec), read_write=[workdir])
    else:
        try:
            tc = toolchain.LocalToolchain.from_settings(settings)
        except toolchain.ToolchainMissingError as exc:
            raise CliError(str(exc)) from exc
    try:
        built = cache.build(
            tree, target_id, tc, workdir, spec=spec, install=bool(args.install) and not args.sandbox
        )
        manifest, archive = cache.pack(built, graph_commit=commit, target_id=target_id, spec=spec)
    except (cache.CacheError, graphmod.GraphError, toolchain.ToolchainMissingError) as exc:
        sys.stdout.write(json.dumps({"ok": False, "error": str(exc)}) + "\n")
        sys.stderr.write(f"opn-gate: cache not published: {exc}\n")
        return EXIT_FAIL
    (out_dir / cache.MANIFEST).write_bytes(manifest)
    (out_dir / cache.ARCHIVE).write_bytes(archive)
    doc: dict[str, Any] = {
        "ok": True,
        "target": target_id,
        "commit": commit,
        "modules": sorted(built.modules),
        "archive_bytes": len(archive),
        "archive_sha256": cache.sha256(archive),
        "manifest": str(out_dir / cache.MANIFEST),
        "uploaded": False,
    }
    if args.bucket:
        try:
            store = objectstore.S3Store(args.bucket, prefix=args.prefix)
            cache.upload(store, target_id, commit, manifest, archive)
        except objectstore.ObjectStoreError as exc:
            doc["ok"] = False
            doc["error"] = str(exc)
            sys.stdout.write(json.dumps(doc, indent=2) + "\n")
            sys.stderr.write(f"opn-gate: cache built but not uploaded: {exc}\n")
            return EXIT_FAIL
        doc["uploaded"] = True
        doc["keys"] = [cache.archive_key(target_id, commit), cache.manifest_key(target_id, commit)]
    sys.stdout.write(json.dumps(doc, indent=2) + "\n")
    return EXIT_PASS


def run_sign(args: argparse.Namespace, settings: config.Settings) -> int:
    """Sign with the gate key read through config (C8); verify against the committed public key."""
    if not settings.gate_signing_key:
        msg = "OPN_GATE_SIGNING_KEY is not set"
        raise CliError(msg)
    doc = schemas.load_json(args.attestation)
    if doc.get("schema") not in attestation.ACCEPTED_SCHEMAS:
        msg = f"not an attestation: schema {doc.get('schema')!r}"
        raise CliError(msg)
    public_key = args.public_key.read_text(encoding="utf-8")
    s = signer.SshKeygenSigner()
    with tempfile.TemporaryDirectory(prefix="opn-gate-key-") as tmp:
        key_path = Path(tmp) / "gate"
        key_path.touch(mode=0o600)
        key_path.write_text(settings.gate_signing_key.rstrip("\n") + "\n", encoding="utf-8")
        signed = postmerge.sign_gate(doc, key_path=key_path, signer=s)
    if not postmerge.verify(signed, public_key, s):
        msg = f"signature does not verify against {args.public_key}; wrong key?"
        raise CliError(msg)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(schemas.canonical_json(signed))
    sys.stdout.write(json.dumps({"signed": str(args.out), "key_id": signed["signature"]["key_id"]}))
    sys.stdout.write("\n")
    return EXIT_PASS


# --- the curator's commands (F08-R9 to R12) ------------------------------------------------------


def _graph_and_target(args: argparse.Namespace) -> tuple[Path, str]:
    """The checkout and the target every curator command works on, both checked to exist."""
    graph: Path = args.graph.resolve()
    if not graph.is_dir():
        msg = f"graph checkout not found: {graph}"
        raise CliError(msg)
    target_id = args.target or infer_target(graph)
    if not layout.graph_nodes_dir(graph, target_id).is_dir():
        msg = f"target {target_id!r} has no nodes directory in {graph}"
        raise CliError(msg)
    return graph, target_id


def _curator_common(args: argparse.Namespace) -> tuple[Path, str, str]:
    graph, target_id = _graph_and_target(args)
    date = args.date or attestation.utc_now().strftime(DATE_FORMAT)
    try:  # a malformed flag is a usage error, not a schema refusal after the work
        datetime.strptime(date, DATE_FORMAT).replace(tzinfo=UTC)
    except ValueError:
        msg = f"--date must be a UTC timestamp like 2026-09-10T12:13:14Z, got {date!r}"
        raise CliError(msg) from None
    return graph, target_id, date


def _curator_branch(graph: Path, branch: str, message: str, written: Sequence[str]) -> None:
    """A branch and one commit holding what a command wrote — the curator's pull request is
    then `git push` and `gh pr create`, under the curator's own credentials, which the gate
    never holds (C8; F08-Q17)."""
    if _git(graph, "rev-parse", "--is-inside-work-tree").returncode != 0:
        msg = f"--branch needs a git checkout; {graph} is not one"
        raise CliError(msg)
    for step in (
        ["checkout", "-q", "-b", branch],
        ["add", "--", *written],
        ["commit", "-q", "-m", message],
    ):
        proc = _git(graph, *step)
        if proc.returncode != 0:
            msg = f"git {step[0]} failed: {proc.stderr.strip()}"
            raise CliError(msg)


def _emit_curator(doc: dict[str, Any], graph: Path, branch: str | None, message: str) -> int:
    if branch:
        _curator_branch(graph, branch, message, [str(p) for p in doc.get("written", [])])
        doc["branch"] = branch
        doc["next"] = f"git push -u origin {branch} && gh pr create --fill"
    sys.stdout.write(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
    return EXIT_PASS


def run_revise(args: argparse.Namespace, settings: config.Settings) -> int:
    graph, target_id, date = _curator_common(args)
    statement = _read_flag_file(args.statement, "--statement")
    if not args.request.is_file():
        msg = f"--request {args.request} is not a file"
        raise CliError(msg)
    revision = curator.revise(
        graph, target_id, args.node_id, statement, args.request, author=args.author, date=date
    )
    doc = {"ok": True, **revision.as_dict()}
    return _emit_curator(doc, graph, args.branch, f"revise: {args.node_id} -> {revision.new_id}")


def run_consolidate(args: argparse.Namespace, settings: config.Settings) -> int:
    graph, target_id, date = _curator_common(args)
    defeq: curator.Defeq | None = None
    if not args.no_toolchain:
        spec_path = layout.gate_spec_path(graph, target_id)
        try:
            spec = schemas.load_json(spec_path, "gate-spec/v1")
        except schemas.SchemaError as exc:
            msg = f"cannot load {spec_path}: {exc}"
            raise CliError(msg) from exc
        out_dir = _out_dir(args.out, "opn-consolidate-")
        workdir = out_dir / "work"
        tc: toolchain.Toolchain
        if args.sandbox:
            tag = args.image or ensure_image(spec, build=not args.no_build)
            tc = sandbox.SandboxToolchain(tag, sandbox.Caps.from_spec(spec), read_write=[workdir])
        else:
            try:
                tc = toolchain.LocalToolchain.from_settings(settings)
            except toolchain.ToolchainMissingError as exc:
                raise CliError(str(exc)) from exc
        ctx = RunContext(
            graph_root=graph,
            claim=Claim(target_id, args.keep),
            spec=spec,
            gate_spec_hash=schemas.content_hash(spec_path.read_bytes()),
            changes=None,
            workdir=workdir,
            toolchain=tc,
            settings=settings,
            install_toolchain=bool(args.install) and not args.sandbox,
        )

        def defeq(kept: layout.Node, dropped: layout.Node) -> bool:
            return curator.statements_defeq(ctx, kept, dropped)

    record = curator.consolidate(
        graph, target_id, args.keep, args.drop, author=args.author, date=date, defeq=defeq
    )
    written = [record.resolve().relative_to(graph).as_posix()]
    doc = {"ok": True, "keep": args.keep, "drop": args.drop, "written": written}
    return _emit_curator(doc, graph, args.branch, f"consolidate: {args.drop} into {args.keep}")


def run_status(args: argparse.Namespace, settings: config.Settings) -> int:
    graph, target_id, date = _curator_common(args)
    now = attestation.utc_now()
    record = curator.declare_status(
        graph,
        target_id,
        args.ref,
        args.status,
        args.cause,
        author=args.author,
        date=date,
        now=now,
        last_merge=last_progress_merge(graph, target_id),
        k=args.k,
        n_days=args.n,
    )
    written = [record.resolve().relative_to(graph).as_posix()]
    doc = {"ok": True, "ref": args.ref, "status": args.status, "written": written}
    return _emit_curator(doc, graph, args.branch, f"status: {args.ref} {args.status}")


# --- intake and fidelity (F11-R2, R3, R5) ----------------------------------------------------


def _intake_graph(args: argparse.Namespace) -> Path:
    """The checkout an intake command works on. Unlike the curator's commands this cannot ask
    for the target's nodes directory: ``intake new`` is what creates it."""
    graph: Path = args.graph.resolve()
    if not graph.is_dir():
        msg = f"graph checkout not found: {graph}"
        raise CliError(msg)
    return graph


def _intake_date(args: argparse.Namespace) -> str:
    date = args.date or attestation.utc_now().strftime(DATE_FORMAT)
    try:
        datetime.strptime(date, DATE_FORMAT).replace(tzinfo=UTC)
    except ValueError:
        msg = f"--date must be a UTC timestamp like 2026-09-10T12:13:14Z, got {date!r}"
        raise CliError(msg) from None
    return date


def spec_template(graph: Path, given: Path | None) -> dict[str, Any]:
    """R2: the gate settings the new target inherits.

    Inherited rather than invented, and inherited from the *graph* rather than from this repo:
    the axiom allowlist, the hazard checkers and the step-3 caps are what the graph's own gate
    runs under (D-35), and a target quietly listed under a different allowlist would be a second
    trust base. With no single answer in the graph the curator has to say which one.
    """
    if given is not None:
        return schemas.load_json(given.resolve(), "gate-spec/v1")
    existing = (
        sorted(p for p in (graph / "targets").glob("*/gate-spec.json") if p.is_file())
        if (graph / "targets").is_dir()
        else []
    )
    if not existing:
        msg = "this graph has no target to inherit gate settings from; pass --spec"
        raise CliError(msg)
    specs = [schemas.load_json(p, "gate-spec/v1") for p in existing]
    shared = {k: v for k, v in specs[0].items() if k not in ("graph_id", "mathlib_sha")}
    for spec in specs[1:]:
        if {k: v for k, v in spec.items() if k not in ("graph_id", "mathlib_sha")} != shared:
            msg = "this graph's targets do not agree on one gate-spec; pass --spec"
            raise CliError(msg)
    return specs[0]


def intake_checker(
    graph: Path, target_id: str, args: argparse.Namespace, settings: config.Settings
) -> intake.Checker:
    """R2's admission seam, wired to the real thing: F08's admission for the root node, and a
    plain elaboration for each definition, which is all a ``defs/`` file can be asked.

    Both run wherever the caller says — ``--sandbox`` puts them in the step-3 image, which is
    where the authoritative gate will run them (C9).
    """
    spec_path = layout.gate_spec_path(graph, target_id)
    out_dir = _out_dir(getattr(args, "out", None), "opn-intake-")

    def check(path: Path, subject: str) -> intake.SubjectCheck:
        spec = schemas.load_json(spec_path, "gate-spec/v1")
        workdir = out_dir / subject / "work"
        workdir.mkdir(parents=True, exist_ok=True)
        tc: toolchain.Toolchain
        if args.sandbox:
            tag = args.image or ensure_image(spec, build=not args.no_build)
            tc = sandbox.SandboxToolchain(
                tag, sandbox.Caps.from_spec(spec), read_only=[path], read_write=[workdir]
            )
        else:
            try:
                tc = toolchain.LocalToolchain.from_settings(settings)
            except toolchain.ToolchainMissingError as exc:
                raise CliError(str(exc)) from exc
        ctx = RunContext(
            graph_root=graph,
            claim=Claim(target_id, path.name if path.is_dir() else subject),
            spec=spec,
            gate_spec_hash=schemas.content_hash(spec_path.read_bytes()),
            changes=None,
            workdir=workdir,
            toolchain=tc,
            settings=settings,
            install_toolchain=bool(args.install) and not args.sandbox,
        )
        if subject == fidelity.ROOT_SUBJECT:
            result = admit.run(ctx)
            detail = "" if result.admitted else f"{result.first_failing_check}: {result.diagnostic}"
            return intake.SubjectCheck(subject, result.admitted, detail)
        return _elaborate_definition(ctx, path, subject)

    return check


def _elaborate_definition(ctx: RunContext, path: Path, subject: str) -> intake.SubjectCheck:
    """A definition is not a node, so F08's admission does not apply to it; what does is that it
    elaborates at all — with the definitions it imports built first, in their order, which is
    ``opn_gate.defs``'s job everywhere a Context is compiled (F11-R2; F01-Q2)."""
    resolved = ToolchainStep().run(ctx)
    if not resolved.ok:
        return intake.SubjectCheck(subject, False, "the pinned toolchain is not available")
    tc: toolchain.ResolvedToolchain = ctx.data["toolchain"]
    target_dir = layout.gate_spec_path(ctx.graph_root, ctx.claim.target_id).parent
    problem = defs.compile_all(
        ctx.toolchain, tc, target_dir, ctx.workdir, timeout_s=ctx.wallclock_s
    )
    if problem is None:
        return intake.SubjectCheck(subject, True)
    if problem.details.get("file") == path.name or problem.code in ("defs-cycle", "timeout"):
        messages = problem.details.get("messages") or []
        texts = [str(m.get("text", "")) for m in messages if isinstance(m, dict)][:3]
        return intake.SubjectCheck(subject, False, "; ".join(texts) or problem.message)
    # Another definition failed first; this one is judged once that one is fixed (C7: named).
    return intake.SubjectCheck(subject, False, f"blocked by {problem.message}")


def run_intake(args: argparse.Namespace, settings: config.Settings) -> int:
    graph = _intake_graph(args)
    if args.action == "post":
        written = intake.post(
            graph, args.target_id, venue=args.venue, url=args.url, date=_intake_date(args)
        )
        doc: dict[str, Any] = {"ok": True, "target": args.target_id, "written": list(written)}
        return _emit_curator(doc, graph, args.branch, f"intake: {args.target_id} posted")
    if args.action == "activate":
        written = intake.activate(
            graph, args.target_id, author=args.author, date=_intake_date(args)
        )
        doc = {"ok": True, "target": args.target_id, "written": list(written)}
        return _emit_curator(doc, graph, args.branch, f"intake: {args.target_id} active")
    if args.action == "import-fc":
        return run_import_fc(args, settings, graph)
    record = schemas.load_yaml(args.record.resolve(), intake.SCHEMA)
    checker: intake.Checker = (
        _fake_checker
        if args.no_toolchain
        else intake_checker(graph, args.target_id, args, settings)
    )
    result = intake.new(
        graph,
        args.target_id,
        doc=record,
        root_dir=args.root.resolve(),
        defs_dir=args.defs.resolve() if args.defs else None,
        spec_template=spec_template(graph, args.spec),
        checker=checker,
        author=args.author,
        date=_intake_date(args),
    )
    return _emit_curator(
        {"ok": True, **result.as_dict()}, graph, args.branch, f"intake: list {args.target_id}"
    )


def _fake_checker(path: Path, subject: str) -> intake.SubjectCheck:
    return intake.SubjectCheck(subject, True, "admission skipped (--no-toolchain)")


def run_import_fc(args: argparse.Namespace, settings: config.Settings, graph: Path) -> int:
    """R9: one Formal Conjectures statement, copied in under its own licence.

    The curator's half of the record comes in as a file (`--from`): prior art, domains, the title
    and the paraphrase are what only a person can write. The upstream half — provenance, sources
    and the track — is derived from the import, so a copied target cannot describe itself as
    anything but a copy.
    """
    base = schemas.load_yaml(args.record.resolve(), intake.SCHEMA)
    checker: intake.Checker = (
        _fake_checker
        if args.no_toolchain
        else intake_checker(graph, args.target_id, args, settings)
    )
    result = intake.import_fc(
        graph,
        args.target_id,
        source=args.source.resolve(),
        rel_path=args.rel_path,
        commit=args.commit,
        base=base,
        witness=_read_flag_file(args.witness, "--witness"),
        statement=(_read_flag_file(args.statement, "--statement") if args.statement else None),
        repo=args.repo,
        url=args.url,
        licence=args.licence,
        attribution=args.attribution,
        upstream_author=args.upstream_author,
        spec_template=spec_template(graph, args.spec),
        checker=checker,
        author=args.author,
        date=_intake_date(args),
        listed_max=settings.listed_targets_max,
    )
    doc: dict[str, Any] = {"ok": True, **result.as_dict()}
    doc["written"] = [*doc.get("written", []), result.notice]
    return _emit_curator(doc, graph, args.branch, f"intake: import {args.target_id}")


def run_fidelity(args: argparse.Namespace, settings: config.Settings) -> int:
    """R3: append one certificate, and print the grade the target now derives from the set."""
    graph = _intake_graph(args)
    directory = intake.target_dir(graph, args.target_id)
    evidence = _read_flag_file(args.evidence, "--evidence")
    path = fidelity.attest(
        directory,
        args.subject,
        args.grade,
        attestor=args.by,
        subject_author=args.subject_author,
        date=_intake_date(args)[:10],
        evidence=evidence,
    )
    doc: dict[str, Any] = {
        "ok": True,
        "target": args.target_id,
        "subject": args.subject,
        "grade": args.grade,
        "target_grade": fidelity.target_grade(directory),
        "subjects": [row.as_dict() for row in fidelity.subject_grades(directory)],
        "written": [path.resolve().relative_to(graph.resolve()).as_posix()],
    }
    message = f"fidelity: {args.target_id} {args.subject} {args.grade}"
    return _emit_curator(doc, graph, args.branch, message)


# --- qa (F12-R3, R4) ------------------------------------------------------------------------------


def _qa_context(
    args: argparse.Namespace, settings: config.Settings, graph: Path, target_id: str
) -> RunContext:
    """The root's node directory as a ``node_context``: the screens are checks on one node in a
    graph checkout, sandboxed the way admission is (C9)."""
    target_dir = intake.target_dir(graph, target_id)
    if not target_dir.is_dir():
        msg = f"no such target: {target_id} under {graph}"
        raise CliError(msg)
    root = qa.root_node(target_dir)
    node_args = argparse.Namespace(**vars(args))
    node_args.node_dir = layout.graph_nodes_dir(graph, target_id) / root
    return node_context(node_args, settings, prefix="opn-qa-", sandboxed=bool(args.sandbox))


def run_qa(args: argparse.Namespace, settings: config.Settings) -> int:
    graph = _intake_graph(args)
    date = _intake_date(args)
    target_dir = intake.target_dir(graph, args.target_id)
    if args.action == "route":
        root = qa.root_node(target_dir)
        node = curator.load_node(
            layout.graph_nodes_dir(graph, args.target_id), args.target_id, root
        )
        written = qa.route_finding(
            target_dir,
            node,
            args.claim,
            reading=args.reading,
            defect_class=args.defect_class,
            contributor=args.by,
            date=date,
            note=args.note,
        )
        doc: dict[str, Any] = {
            "ok": True,
            "target": args.target_id,
            "routed": args.claim,
            "reading": args.reading,
            "written": [written],
        }
        return _emit_curator(doc, graph, args.branch, f"qa: route {args.claim} ({args.reading})")
    if args.action == "backtranslate":
        layer = qa.backtranslate(target_dir, args.subject, model=_model_client(settings), date=date)
        return _emit_layer(layer, graph, args)
    ctx = _qa_context(args, settings, graph, args.target_id)
    if args.action == "brief":
        layer = qa.brief(
            ctx,
            args.subject,
            model=_model_client(settings),
            date=date,
            timeout_s=settings.qa_attempt_budget_s,
        )
        return _emit_layer(layer, graph, args)
    if args.action == "equivalence":
        if args.subject != fidelity.ROOT_SUBJECT:
            msg = "an equivalence is between the root and another node; the subject is `root`"
            raise CliError(msg)
        layer = qa.equivalence(
            ctx, args.other, date=date, attempt_budget_s=settings.qa_attempt_budget_s
        )
        return _emit_layer(layer, graph, args)
    run = qa.screen(
        ctx,
        args.subject,
        date=date,
        attempt_budget_s=settings.qa_attempt_budget_s,
        subject_budget_s=settings.qa_subject_budget_s,
        contributor=args.by,
    )
    doc = {
        "ok": run.clean,
        "target": args.target_id,
        "sandboxed": bool(args.sandbox),
        **run.as_dict(),
    }
    if args.branch:
        _curator_branch(
            graph, args.branch, f"qa: screen {args.target_id} {args.subject}", run.written
        )
        doc["branch"] = args.branch
        doc["next"] = f"git push -u origin {args.branch} && gh pr create --fill"
    sys.stdout.write(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
    if not run.clean:
        what = (
            f"findings: {', '.join(r.check for r in run.findings)}"
            if run.findings
            else "not a clean pass: " + ", ".join(r.check for r in run.rows if r.verdict != "pass")
        )
        sys.stderr.write(f"opn-gate: qa screen {args.target_id}/{args.subject}: {what}\n")
    # R3: a success is a rejection — a finding exits non-zero; so does anything short of a
    # clean pass, because an inconclusive screen is not one either (C7).
    return EXIT_PASS if run.clean else EXIT_FAIL


def _model_client(settings: config.Settings) -> models.ModelClient:
    """The model seam, or a usage error before any work when no key is configured (C8)."""
    if not settings.model_api_key:
        msg = (
            "OPN_MODEL_API_KEY is not set; the brief and the back-translation ask a model "
            "(F12-R6, R7) and the key lives in the curator's .env (C8)"
        )
        raise CliError(msg)
    return models.HttpxModelClient(settings.model_api_key, settings.model)


def _emit_layer(layer: qa.LayerRun, graph: Path, args: argparse.Namespace) -> int:
    doc: dict[str, Any] = {"target": args.target_id, **layer.as_dict()}
    if args.branch:
        message = f"qa: {args.action} {args.target_id} {args.subject}"
        _curator_branch(graph, args.branch, message, doc["written"])
        doc["branch"] = args.branch
        doc["next"] = f"git push -u origin {args.branch} && gh pr create --fill"
    sys.stdout.write(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
    if not layer.ok:
        sys.stderr.write(f"opn-gate: qa {args.action}: {layer.row.note}\n")
    return EXIT_PASS if layer.ok else EXIT_FAIL


def last_progress_merge(graph: Path, target_id: str) -> datetime | None:
    """When the target's nodes last changed on ``main``'s history — the latest commit touching
    them, which is a merge or the bot's products commit (D-33 a). ``None`` for a bare tree."""
    if _git(graph, "rev-parse", "--is-inside-work-tree").returncode != 0:
        return None
    proc = _git(graph, "log", "-1", "--format=%cI", "--", f"targets/{target_id}/nodes")
    when = proc.stdout.strip()
    if proc.returncode != 0 or not when:
        return None
    return datetime.fromisoformat(when).astimezone(UTC)


def run_missing_library(args: argparse.Namespace, settings: config.Settings) -> int:
    graph, target_id = _graph_and_target(args)
    report = curator.missing_library_report(graph, target_id, threshold=args.threshold)
    doc = {
        "target": target_id,
        "threshold": args.threshold,
        "lemmas": [m.as_dict() for m in report],
        "created": [],  # D-13, F08-Q3: the curator proposes; nothing is created here
    }
    sys.stdout.write(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
    return EXIT_PASS


def run_ledger(args: argparse.Namespace, settings: config.Settings) -> int:
    """F08-R13: after a proposal merges, the proposer's statement line — for a variant or a
    speculative crux, never a hole (D-31) and never a revision (D-19)."""
    graph, commit = _checkout_and_commit(args.graph, args.commit)
    classification = modes.classify(commit_changes(graph, commit), author=settings.pr_author)
    roles = {loc.role for loc in classification.located}
    nothing: dict[str, Any] = {"earned": False, "commit": commit}
    if classification.mode != "proposal" or classification.admit is None or "node" not in roles:
        nothing["reason"] = f"not a merged node proposal (mode {classification.mode!r})"
        sys.stdout.write(json.dumps(nothing, indent=2) + "\n")
        return EXIT_PASS
    target_id, node_id = str(classification.target_id), classification.admit
    meta = schemas.load_yaml(layout.graph_nodes_dir(graph, target_id) / node_id / "META.yaml")
    identity = proposer_of(graph, commit)
    entry = ledger.statement_entry(
        identity=identity,
        target=target_id,
        node=node_id,
        origin=str(meta.get("origin")),
        merge_commit=commit,
        date=graphmod.commit_timestamp(graph, commit),
        tutorial=bool(meta.get("tutorial", False)),
        supersedes=str(meta["supersedes"]) if meta.get("supersedes") else None,
    )
    if entry is None:
        nothing["reason"] = f"{node_id} ({meta.get('origin')}) earns no statement line (D-19, D-31)"
        sys.stdout.write(json.dumps(nothing, indent=2) + "\n")
        return EXIT_PASS
    try:
        path = ledger.record(graph, identity, entry)
    except schemas.SchemaError as exc:
        nothing["reason"] = f"identity {identity!r} cannot hold a ledger: {exc}"
        sys.stdout.write(json.dumps(nothing, indent=2) + "\n")
        return EXIT_PASS
    assert path is not None
    doc = {
        "earned": True,
        "identity": identity,
        "node": node_id,
        "line": entry.line,
        "written": path.resolve().relative_to(graph).as_posix(),
    }
    sys.stdout.write(json.dumps(doc, indent=2) + "\n")
    return EXIT_PASS


def proposer_of(graph: Path, commit: str) -> str:
    """The ledger identity behind a merge: the author of the pull request's commit (F07-R2 puts
    the pseudonym there) — the second parent's for a merge commit, the commit's own otherwise."""
    head = (
        f"{commit}^2"
        if _git(graph, "rev-parse", "--verify", "--quiet", f"{commit}^2").returncode == 0
        else commit
    )
    return _git(graph, "log", "-1", "--format=%an", head).stdout.strip()


def _checkout_and_commit(graph_arg: Path, ref: str) -> tuple[Path, str]:
    graph = graph_arg.resolve()
    if _git(graph, "rev-parse", "--is-inside-work-tree").returncode != 0:
        msg = f"{graph} is not a git checkout"
        raise CliError(msg)
    commit = _git(graph, "rev-parse", "--verify", f"{ref}^{{commit}}").stdout.strip()
    if not commit:
        msg = f"unknown commit {ref!r}"
        raise CliError(msg)
    return graph, commit


def _out_dir(out: Path | None, prefix: str) -> Path:
    out_dir = (out or Path(tempfile.mkdtemp(prefix=prefix))).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def _sandboxed_context(  # noqa: PLR0913 — one argument per CLI flag
    graph: Path,
    commit: str,
    out_dir: Path,
    *,
    target: str | None,
    node: str,
    settings: config.Settings,
    image: str | None,
    no_build: bool,
) -> RunContext:
    """Export the tree at ``commit`` and build a RunContext whose toolchain is the sandbox."""
    tree = export_tree(graph, commit, out_dir / "tree")
    target_id = target or infer_target(tree)
    spec_path = layout.gate_spec_path(tree, target_id)
    try:
        spec = schemas.load_json(spec_path, "gate-spec/v1")
    except schemas.SchemaError as exc:
        msg = f"cannot load {spec_path}: {exc}"
        raise CliError(msg) from exc
    tag = image or ensure_image(spec, build=not no_build)
    node_dir = layout.graph_nodes_dir(tree, target_id) / node
    workdir = out_dir / "work"
    tc = sandbox.SandboxToolchain(
        tag, sandbox.Caps.from_spec(spec), read_only=[node_dir], read_write=[workdir]
    )
    return RunContext(
        graph_root=tree,
        claim=Claim(target_id, node),
        spec=spec,
        gate_spec_hash=schemas.content_hash(spec_path.read_bytes()),
        changes=commit_changes(graph, commit),
        workdir=workdir,
        toolchain=tc,
        settings=settings,
    )


def export_tree(graph: Path, commit: str, dest: Path) -> Path:
    """The graph's tree at ``commit`` as plain files (no .git), via git archive."""
    dest.mkdir(parents=True, exist_ok=True)
    archive = subprocess.run(
        ["git", "-C", str(graph), "archive", "--format=tar", commit],
        capture_output=True,
        check=True,
        env=git_environment(),
    )
    subprocess.run(["tar", "-x", "-C", str(dest)], input=archive.stdout, check=True)
    return dest


def commit_changes(graph: Path, commit: str) -> list[Change]:
    """What ``commit`` changed against its first parent (a merge: the whole PR)."""
    parent = _git(graph, "rev-parse", "--verify", "--quiet", f"{commit}^")
    if parent.returncode != 0:
        return []
    diff = _git(graph, "diff", "--name-status", "--no-renames", f"{commit}^", commit)
    return paths.changes_from_name_status(diff.stdout)


def ensure_image(spec: dict[str, Any], *, build: bool) -> str:
    """The image every sandboxed run uses, from the graph's gate-spec alone (F10-R5, Q10).

    A graph that pins ``devcontainer_ref`` names the published image by digest, and that digest
    is what the authoritative gate, the precheck job, ``reproduce.sh`` and the devcontainer all
    run — pulled once if absent, never built. A graph that pins none (the fixtures, a graph
    before its first pin) gets the image built from ``gate/Dockerfile`` for its toolchain, as
    before; ``--no-build`` then requires it to be present already.
    """
    ref = spec.get("devcontainer_ref")
    if isinstance(ref, str) and ref:
        if sandbox.image_exists(ref):
            return ref
        log.info("pulling the pinned image %s", ref)
        try:
            return sandbox.pull_image(ref)
        except sandbox.SandboxError as exc:
            raise CliError(str(exc)) from exc
    lean_toolchain = str(spec["lean_toolchain"])
    raw_sha = spec.get("mathlib_sha")
    mathlib_sha = str(raw_sha) if raw_sha else None
    tag = sandbox.image_tag(lean_toolchain, mathlib_sha)
    if sandbox.image_exists(tag):
        return tag
    if not build:
        msg = f"sandbox image {tag} is not present; build it from gate/Dockerfile"
        raise CliError(msg)
    log.info("building sandbox image %s", tag)
    return sandbox.build_image(GATE_DIR, lean_toolchain, mathlib_sha=mathlib_sha)


def infer_target(graph: Path) -> str:
    targets = sorted(p.name for p in (graph / "targets").iterdir() if p.is_dir())
    if len(targets) != 1:
        msg = f"--target is required; graph has targets {targets}"
        raise CliError(msg)
    return targets[0]


def _git(graph: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """``git -C <graph> ...`` on the graph checkout and nothing else: the repository variables
    git exports to a hook are dropped, or a pre-commit hook running the gate from a worktree
    would see ``--branch`` check out and stage in the repository that ran the hook (F08-Q18)."""
    return subprocess.run(
        ["git", "-C", str(graph), *args],
        capture_output=True,
        text=True,
        check=False,
        env=git_environment(),
    )


def git_environment() -> dict[str, str]:
    return config.child_environment(drop=config.GIT_REPO_VARIABLES)


def worktree_changes(graph: Path, base: str | None) -> list[Change] | None:
    """Tracked changes against ``base`` plus untracked files; ``None`` when not a git checkout."""
    if _git(graph, "rev-parse", "--is-inside-work-tree").returncode != 0:
        log.warning("%s is not a git checkout; step 2 runs without a diff", graph)
        return None
    ref = base or "HEAD"
    diff = _git(graph, "diff", "--name-status", "--no-renames", ref, "--")
    if diff.returncode != 0:
        msg = f"git diff against {ref!r} failed: {diff.stderr.strip()}"
        raise CliError(msg)
    changes = paths.changes_from_name_status(diff.stdout)
    untracked = _git(graph, "ls-files", "--others", "--exclude-standard")
    changes.extend(Change("A", line.strip()) for line in untracked.stdout.splitlines() if line)
    return changes


def clean_head(graph: Path) -> str | None:
    """HEAD's sha when the tree is exactly that commit; ``None`` for a dirty or non-git tree."""
    if _git(graph, "rev-parse", "--is-inside-work-tree").returncode != 0:
        return None
    status = _git(graph, "status", "--porcelain")
    if status.stdout.strip():
        return None
    head = _git(graph, "rev-parse", "HEAD")
    return head.stdout.strip() if head.returncode == 0 else None


if __name__ == "__main__":
    sys.exit(main())
