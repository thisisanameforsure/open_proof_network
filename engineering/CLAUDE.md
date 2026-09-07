# Open Proof Network — build instructions for Claude

A distributed crowdsourced Lean 4 proof network for open mathematical problems, built spec-first.
The protocol is decided (`docs/architecture_decisions_v_3_10.html`, decisions D-1 to D-36 with
frozen identifiers); the implementation stack is locked (conventions §1). Everything in
`engineering/` is about how to build it, not what it is (`engineering/README.md`). The workflow
below is in force from the first line of code.

## Two repositories (D-35)

- **This repo is `network`**: `gate/`, `api/`, `site/` at the root, plus `AGENTS.md`. It has no
  authority of its own; a graph pins the commit of this repo whose gate runs on it.
- **The graph repo is `../open_proof_network_graph`**, a sibling directory, the `graph` of D-35.
  Its history is mathematics only. Build work touches it only for the files D-35 places there
  (`.github/workflows/gate.yml`, `schemas/`, seeded targets and nodes), and a task that does so
  lists those paths with the `../open_proof_network_graph/` prefix in its Files column.
- **Specs, evidence, and the task ledger live here, never in the graph repo.** A commit to the
  graph repo made by a build task carries the same `FXX-Tn:` message as its commit here, so the two
  histories cross-reference; the evidence for it is captured in this repo.
- **Gate tests run against fixture graphs kept in this repo**, never against the live graph repo.

The law of the project:

1. **Read `engineering/specs/constitution.html` first, every session.** Non-negotiables. If code
   and the constitution conflict, the constitution wins.
2. **Work from specs.** The current feature's spec is `engineering/specs/features/FXX.html` —
   EARS requirements, acceptance criteria each naming a test case, dependency-ordered tasks each
   with a verification command. Build order and status: `engineering/specs/index.html`.
3. **Conventions are binding:** `engineering/specs/conventions.html` — architecture (§1),
   testing (§2), verification-as-evidence (§3), security (§4), errors/logging (§5), git & session
   protocol (§6), spec format (§7).
4. **Specs cite the architecture decisions by D-number; they never restate or override one.** A
   deviation is logged in the spec as a proposed overturn, and the decision changes only through
   the architecture doc's own process.

## Session protocol (conventions §6)

- **Start:** read constitution → current spec → task ledger (the **Tasks:** line in the spec's §10
  Status block). State what this session will do. `/session-start` runs this ritual.
- **A task is done only when its named verification command has run and passed**, output captured
  to `engineering/evidence/FXX/`. Visual work: screenshot too. No "looks good" gates.
  `make verify` runs the full suite (regression gate; also runs as the pre-commit hook — enable
  once per clone with `git config core.hooksPath .githooks`).
- **Commit per verified task:** message `FXX-Tn: description`. Evidence committed with it. Update
  the spec's **Tasks:** ledger line and the feature's Status cell in
  `engineering/specs/index.html` in the same commit.
- **Feature complete:** tag it `FXX-done`; update the Status column in
  `engineering/specs/index.html`; prune the `## Log` section below to lessons still relevant.
- **End:** spec status updated; docs stay current or the session isn't done.
- **No drive-by refactors** outside the current task's files.

## Context docs

- `AGENTS.md` — what this repo is and its relation to the graph repo (D-35).
- `engineering/specs/constitution.html` — non-negotiables (read first).
- `engineering/specs/conventions.html` — how we build.
- `engineering/specs/index.html` — feature build order and status.
- `docs/architecture_decisions_v_3_10.html` — the protocol: every decision with its rationale and
  overturning condition, the stages, the glossary. Cite decisions by D-number.

## Current state (2026-09-07)

- Spec site scaffolded from the ordertime_plugin structure, then split: `engineering/` holds how
  we build, `docs/` holds what is built. Constitution C1–C10 in force; conventions §1/§2 filled.
- **Stack locked 2026-09-07** (conventions §1): Python 3.13 + uv, pytest/ruff/mypy, jsonschema;
  gate on GitHub-hosted runners, api + MCP on Lambda, precheck as an Actions job in a scratch
  repo, site on S3/CloudFront — "boxless" at Stage 0. Two mandatory test tiers (§2).
- Decisions doc at v3.10: the network is two repositories (D-35) plus a disposable precheck
  scratch repo. This repo is `network`; the graph repo `../open_proof_network_graph` exists as an
  empty initial commit.
- Stage 0 roadmap F00–F11 in `engineering/specs/index.html`, every feature specced 2026-09-07
  (F07/F08 split submissions from proposals). Current feature: F00 (gate walking skeleton), no
  task started. Later specs will need touch-ups as earlier features land; each carries the
  protocol readings it relies on in its §9 so a drift is visible.
- No domain or DNS exists yet; the site ships on CloudFront's issued hostname (F04).

## Log

- 2026-09-07 — Stack lock came out of a grill session, not a doc pass; the rationale is recorded
  inline in conventions §1/§2 so it can be overturned with evidence. Two calls worth remembering:
  self-hosted GitHub runners were rejected for the gate on GitHub's own public-repo guidance
  (any PR can run code on them), and Lean elaboration executes arbitrary code, so precheck is
  never run outside the same sandbox the gate uses.
- 2026-09-07 — Specs F01–F11 surfaced seven protocol readings; Mike folded all into decisions
  v3.10 by survey rather than leaving them as §9 flags. Pattern to keep: when a spec cannot follow
  a decision as written, ask, then change the doc — a spec flag that outlives the session rots.
