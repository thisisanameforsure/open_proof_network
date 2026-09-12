"""F10-T3 / R5, R6, AC5: pin a published gate image, by digest, in a graph — and check the pin.

    uv run python gate/tools/pin_image.py <name@sha256:...> --graph PATH --target ID
                                          [--network-commit SHA] [--cache-url URL] [--api-url URL]
    uv run python gate/tools/pin_image.py --check --graph PATH --target ID [--verify]

Pinning writes two files in the graph, the gate owner's visible diff (D-4, D-35):
``targets/<target>/gate-spec.json`` gains ``devcontainer_ref`` (and ``network_commit`` when
given, since the image is built at that commit and the two should move together; and
``olean_cache_url`` when given, F10-R7), and
``.devcontainer/devcontainer.json`` is written to run that image (F10-R6). Nothing else names
the image: ``gate.yml``, the precheck job and ``reproduce.sh`` all reach it through
``opn_gate.cli.ensure_image``, which reads the spec (F10-Q10), so one digest serves all four
by construction.

``--check`` reads the pin back: the reference is a digest, the devcontainer runs the same one,
the post-create command is the network's script, and none of the three workflow or script files
carries an image of its own. ``--verify`` additionally pulls the digest and compares the image's
``org.opencontainers.image.revision`` label with the pinned network commit (network tier).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # gate/ on the path for opn_gate

from opn_gate import layout, sandbox, schemas

ROOT = Path(__file__).resolve().parents[2]
DEVCONTAINER = Path(".devcontainer") / "devcontainer.json"
POST_CREATE = "bash /opt/opn/network/gate/devcontainer/post-create.sh"
NETWORK_IN_IMAGE = "/opt/opn/network"
REVISION_LABEL = "org.opencontainers.image.revision"
#: F11-R6: the Mathlib commit an image carries (empty on a Mathlib-free image); a graph that
#: pins Mathlib must pin an image built for the same commit, or step 1 fails inside the sandbox.
MATHLIB_LABEL = "network.openproof.mathlib_sha"
#: Files that must not name an image of their own (they take it from the spec, Q10).
SPEC_CONSUMERS: tuple[tuple[str, Path], ...] = (
    ("graph", Path(".github/workflows/gate.yml")),
    ("network", Path("gate/precheck/precheck.yml")),
    ("network", Path("gate/reproduce.sh")),
)
IMAGE_MARKERS: tuple[str, ...] = ("ghcr.io/", "@sha256:", "--image ")


def devcontainer_doc(ref: str, target_id: str, *, api_url: str | None) -> dict[str, Any]:
    """The devcontainer.json a graph carries (F10-R6): the pinned image, the network's
    post-create script, the two paths AGENTS.md assumes, and the Lean extension."""
    env: dict[str, str] = {"NETWORK": NETWORK_IN_IMAGE, "GRAPH": "${containerWorkspaceFolder}"}
    if api_url:
        env["OPN_API"] = api_url
    return {
        "name": f"Open Proof Network — {target_id}",
        "image": ref,
        "remoteUser": "opn",
        "containerEnv": env,
        "postCreateCommand": POST_CREATE,
        "customizations": {"vscode": {"extensions": ["leanprover.lean4"]}},
    }


def pin(  # noqa: PLR0913 — one keyword per field the pin may set
    graph: Path,
    target_id: str,
    ref: str,
    *,
    network_commit: str | None,
    api_url: str | None,
    cache_url: str | None = None,
) -> list[Path]:
    """Write the pin; answer the files written. Refuses anything but a digest reference."""
    if not sandbox.is_digest_ref(ref):
        msg = f"not an image digest reference: {ref!r} (expected name@sha256:<64 hex>)"
        raise SystemExit(msg)
    spec_path = layout.gate_spec_path(graph, target_id)
    spec = schemas.load_json(spec_path, "gate-spec/v1")
    spec["devcontainer_ref"] = ref
    if network_commit is not None:
        spec["network_commit"] = network_commit
    if cache_url is not None:
        spec["olean_cache_url"] = cache_url
    spec_path.write_bytes(schemas.canonical_json(schemas.validate(spec, "gate-spec/v1")))
    devcontainer = graph / DEVCONTAINER
    devcontainer.parent.mkdir(parents=True, exist_ok=True)
    devcontainer.write_text(
        json.dumps(devcontainer_doc(ref, target_id, api_url=api_url), indent=2) + "\n",
        encoding="utf-8",
    )
    return [spec_path, devcontainer]


def check(graph: Path, target_id: str, *, network: Path = ROOT) -> list[str]:
    """AC5: every problem with the pin, or ``[]``."""
    problems: list[str] = []
    spec = schemas.load_json(layout.gate_spec_path(graph, target_id), "gate-spec/v1")
    ref = spec.get("devcontainer_ref")
    if not isinstance(ref, str) or not sandbox.is_digest_ref(ref):
        problems.append(f"devcontainer_ref is not an image digest reference: {ref!r}")
    devcontainer = graph / DEVCONTAINER
    if not devcontainer.is_file():
        problems.append(f"{DEVCONTAINER} is missing from the graph")
    else:
        doc = json.loads(devcontainer.read_text(encoding="utf-8"))
        if doc.get("image") != ref:
            problems.append(f"{DEVCONTAINER} runs {doc.get('image')!r}, not the pinned {ref!r}")
        if doc.get("postCreateCommand") != POST_CREATE:
            problems.append(f"{DEVCONTAINER} post-create command is not the network's script")
        if doc.get("remoteUser") != "opn":
            problems.append(f"{DEVCONTAINER} must run as the image's user opn (uid 1000)")
    for where, rel in SPEC_CONSUMERS:
        path = (graph if where == "graph" else network) / rel
        if not path.is_file():
            continue  # a fixture graph carries no workflow; the live one does
        text = path.read_text(encoding="utf-8")
        for marker in IMAGE_MARKERS:
            if marker in text:
                problems.append(f"{rel} names an image itself ({marker!r}); it must use the spec")
    return problems


def verify(
    ref: str, network_commit: str, *, mathlib_sha: str | None = None, docker: str = "docker"
) -> list[str]:
    """Network tier: the pulled image's revision label is the pinned network commit, and its
    Mathlib label is the graph's Mathlib pin (F11-R6) — an image built for another Mathlib, or
    for none, would pass ``--check`` and fail at step 1 inside the sandbox."""
    sandbox.pull_image(ref, docker=docker)
    proc = subprocess.run(
        [docker, "image", "inspect", "--format", "{{json .Config.Labels}}", ref],
        capture_output=True,
        text=True,
        check=True,
    )
    labels = json.loads(proc.stdout or "{}") or {}
    problems: list[str] = []
    revision = labels.get(REVISION_LABEL)
    if revision != network_commit:
        problems.append(
            f"image revision label {revision!r} is not the pinned network commit {network_commit}"
        )
    carried = labels.get(MATHLIB_LABEL) or None
    if carried != mathlib_sha:
        problems.append(
            f"image Mathlib label {carried!r} is not the graph's mathlib_sha {mathlib_sha!r}"
        )
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pin_image", description=__doc__.split("\n\n")[0])
    parser.add_argument("ref", nargs="?", help="the published image, name@sha256:<digest>")
    parser.add_argument("--graph", required=True, type=Path)
    parser.add_argument("--target", required=True)
    parser.add_argument("--network-commit", help="also re-pin network_commit to this sha")
    parser.add_argument("--api-url", help="the service URL the devcontainer exports as OPN_API")
    parser.add_argument(
        "--cache-url", help="also set olean_cache_url (the stack's CacheUrl output)"
    )
    parser.add_argument("--check", action="store_true", help="check the pin instead of writing")
    parser.add_argument("--verify", action="store_true", help="with --check: pull and inspect")
    args = parser.parse_args(argv)
    graph = args.graph.resolve()
    if args.check:
        problems = check(graph, args.target)
        spec = schemas.load_json(layout.gate_spec_path(graph, args.target), "gate-spec/v1")
        if args.verify and not problems:
            raw_sha = spec.get("mathlib_sha")
            problems += verify(
                str(spec["devcontainer_ref"]),
                str(spec["network_commit"]),
                mathlib_sha=str(raw_sha) if raw_sha else None,
            )
        for p in problems:
            print(f"PROBLEM: {p}", file=sys.stderr)
        print("pin ok" if not problems else f"{len(problems)} problem(s)")
        return 0 if not problems else 1
    if not args.ref:
        parser.error("an image reference is required unless --check is given")
    for path in pin(
        graph,
        args.target,
        args.ref,
        network_commit=args.network_commit,
        api_url=args.api_url,
        cache_url=args.cache_url,
    ):
        print(f"wrote {path.relative_to(graph)}")
    print("next: commit both files in the graph (the gate owner's re-pin, D-4)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
