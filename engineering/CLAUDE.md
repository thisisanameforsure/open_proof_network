# Open Proof Network — build instructions for Claude

A distributed crowdsourced Lean 4 proof network for open mathematical problems, built spec-first.
The protocol is decided (`docs/architecture_decisions_v_3_11.html`, decisions D-1 to D-36 with
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
  `engineering/specs/index.html`; prune the `## Log

- 2026-09-07 — Stack lock rationale lives inline in conventions §1/§2 so it can be overturned with
  evidence. Two calls to remember: no self-hosted runners for the gate (any PR can run code on
  them), and contributor Lean never runs outside the gate's sandbox.
- 2026-09-07 — When a spec cannot follow a decision as written, ask, then change the doc; a spec
  flag that outlives the session rots. Applied again 2026-09-08 for D-4 step 9 (v3.11).
- 2026-09-08 — Check upstream before building to a spec's named tool (lean4checker became
  `leanchecker`; `setup-uv` has no `v10` moving tag). Read the README / tag list first.
- 2026-09-08 — One hook per external boundary pays: the sandbox is `LocalToolchain` with `_exec`
  overridden and every pipeline test reused. Never mount over a path a host directory might occupy
  (a tmpfs at `/tmp` hid the sandbox's inputs on Linux CI).
- 2026-09-08 — A pinned tooling commit is chicken-and-egg with its own evidence: pin work takes
  two commits (code, then evidence), at every `gate-spec.json` re-pin.
- 2026-09-08 — Never clean up sandbox containers by age while a real-tier run is in flight: a
  laptop sleep made a live `leanchecker` container look like an hour-old leftover, and removing it
  failed the test it belonged to. Leftovers are identified by the run that owns them, or after it.
- 2026-09-09 — The docker tier builds the step-3 image lazily, from the working tree as it is when
  the first docker test runs, ten minutes into `make verify-lean`. Editing `gate/lean/` during a
  real-tier run put half-written Lean into the image and failed six tests. Stash next-task work
  before an evidence run, or wait.
- 2026-09-09 — A spec that names a future schema version rots as soon as that version ships for
  another reason (F02-R9 said `attestation/v2`; v2 had been taken by the step-9 block a day
  earlier, so `trust_base` became v3, logged as F02-Q5). Specs should say "the next version".
- 2026-09-09 — A graph re-pin is only as good as the seeded nodes under it: F01 changed the
  witness shape and the live tutorial node still had F00's, so the F02 re-pin had to fix
  `Witness.lean` too (D-35 seeded-node exception). Run `pregate.sh` on the live graph after every
  re-pin and keep the output as evidence.
- 2026-09-09 — A *network*-tier acceptance criterion (a real merge on the graph, F03-AC13) cannot
  be met in an unattended session: pushing the graph is the owner's act. Simulate the bot commit
  on a local clone, capture that, and leave the task marked "code complete, evidence pending"
  rather than tagging the feature done.
