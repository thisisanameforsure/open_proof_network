# open_proof_network — the `network` repository

The Open Proof Network is a distributed crowdsourced Lean 4 proof network for open mathematical
problems. Its protocol is `docs/architecture_decisions_v_3_12.html` (decisions D-1 to D-36 with
frozen identifiers). Where anything here disagrees with that document, the document governs.

## Two repositories (D-35)

| Repository | Where | Holds | Authority |
|---|---|---|---|
| `graph` | `../open_proof_network_graph` (sibling directory) | targets, nodes, `defs/`, schemas, attestations, `frontier.json`, `gate-spec.json`; the gate runs as its CI | A merge there is the only thing that changes truth |
| `network` | **this repo** | `gate/` (checks, hazard checkers, `pregate.sh`, `reproduce.sh`, devcontainer, olean-cache pipeline) · `api/` (HTTP endpoints, precheck runner, MCP adapter) · `site/` (static generator) | None of its own: each graph's `gate-spec.json` pins the commit of this repo whose gate runs on it |

Rules that follow, for anyone or any agent working in this repo:

- **The graph repository's history is mathematics only.** Tooling commits, service deploys and
  site changes never land there. Build work touches `../open_proof_network_graph` only for the
  files D-35 places in it (`.github/workflows/gate.yml`, `schemas/`, seeded targets and nodes).
- **Everything in this repo is rebuildable from `graph`.** The trust base is the graph history
  plus the pinned gate; the service, the MCP server and the website may be lost without any
  verdict changing. Nothing here may become a second source of truth.
- **Contributors clone `graph` only.** A prover never needs this repo checked out.
- **A tooling change reaches a graph only as a visible diff to its `gate-spec.json`**, made by the
  gate's named owner (D-4).

## Building this repo

This repo is still being built. Everything about *how* it is built — the build constitution,
conventions, feature specs, task ledger and verification evidence — lives in `engineering/` and is
not part of the protocol. Start at `engineering/README.md`.
