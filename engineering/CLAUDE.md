# Open Proof Network — build instructions for Claude

A distributed crowdsourced Lean 4 proof network for open mathematical problems, built spec-first.
The protocol is decided (`docs/architecture_decisions_v_3_12.html`, decisions D-1 to D-36 with
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
- 2026-09-09 — GitHub's OIDC `sub` claim is now `repo:owner@<id>/name@<id>:ref:...`, so an
  exact-match trust policy on `repo:owner/name:ref:...` is denied. Print the claims from the
  workflow before guessing; pin the trust policy to the numeric ids (they survive renames).
- 2026-09-09 — Adding a schema changes `info.json`'s schema index, which every F03 product
  golden carries. Budget the golden regeneration into the commit that adds the schema, and keep
  the api's fixtures copied from a golden so the two never drift (F05-Q5).
- 2026-09-09 — A workflow on the graph may only use a gate flag the *pinned* commit understands.
  Adding `--claims-url` behind `${VAR:+...}` keeps the old pin working; the flag becomes live
  when the variable is set, which must wait for the re-pin (F05-R10).
- 2026-09-09 — F12 (statement QA, provenance, drift) designed with Mike and settled in
  `engineering/session-notes/2026-09-09-f12-statement-qa.md`; **decisions v3.12 and the F12 spec
  landed 2026-09-10.** Rung two is now `screened-and-signed`, back-translation demoted to one input,
  because the 2026 evidence puts its false-pass rate near a third.
- 2026-09-10 — Renaming a protocol identifier is never free: `back-translated` was an enum value in
  two shipped schemas, and `gate/schemas/HASHES` says versioned, never edited (D-34). So the doc
  leads and the code follows — the v2 bump plus golden regeneration is F11-T2, and
  `PROTOCOL_VERSION` stays `3.11` until it lands, which is why code and doc disagree meanwhile.
  Check for schema enums and file-path constants *before* promising a rename: `site/opn_site/`
  and `api/tests/` both hold the decisions doc's filename, so the version bump breaks tests if the
  rename stops at the docs.
- 2026-09-09 — A domain is configuration when nothing knows its own hostname. The site generator
  and the api both read theirs from config, so `openproofnetwork.org` was two stack parameters
  and a Route 53 zone, with the issued hostnames still answering. Keep it that way: never write
  a hostname into a template or a page.
- 2026-09-09 — GoDaddy cannot alias an apex at CloudFront, and its domain forwarding only runs on
  its own nameservers. Hence the split: the .org is delegated to Route 53, the .com must stay at
  GoDaddy or its redirect to the .org silently dies.
- 2026-09-09 — A deployed acceptance criterion can be blocked by *content* rather than code: F05's
  claim round trip needs a claimable node, and the live graph's only node is proved, so the
  frontier is correctly empty. Do not manufacture graph content to close a criterion — the graph's
  history is mathematics (D-35). Hand the criterion to the feature that will produce that content
  (F11) and say so in both specs.
- 2026-09-09 — Package what the code *reads*, not just what it imports: the Lambda zip carried
  opn_gate but not gate/schemas, so every validating route answered 500 while health stayed green,
  because health validates nothing. A deploy check that only imports modules would not have caught
  it; it verifies the schema files and their pins now.
- 2026-09-09 — Verify an edit landed. Twice a scripted `str.replace` matched nothing (the
  formatter had rewrapped the target line) and the change silently vanished: two rate limits
  stayed at their defaults, and the tests caught it only by luck of covering them. Assert on the
  replacement, or use the Edit tool, which fails loudly.
- 2026-09-09 — Assert the requirement where it is enforced. A precheck attestation records the
  runner it actually ran on, so asserting `hosted` in a laptop test was wrong; the requirement
  belongs to the workflow, and a static check of the YAML proves it — along with the stronger
  property that no step before signing is granted any secret at all.
- 2026-09-09 — Read the shape before asserting on it. Two docker-tier failures (16 minutes each)
  were guesses at the verdict record's field names; the fast tier could not catch them because
  the records only exist after a real run.
- 2026-09-10 — The gate and the api do not run in the same world. The gate shells out to
  `ssh-keygen` because OpenSSH is always where the gate runs; the Lambda image has none, so the
  api verifies SSHSIG in Python instead (F06-Q6). Before reusing a gate helper in the api, ask
  what binary it assumes — a subprocess seam passes every laptop test and fails in production.
- 2026-09-10 — A permission is part of the build, and it is not yours to grant. F06 is code
  complete and blocked on the GitHub App lacking `Actions: write` (403 on dispatch). Probe a
  permission with an *inert* call — dispatching a ref that does not exist gives 403 vs 422 "No
  ref found" and starts no run — and write the probe into the evidence so the founder can check
  it in one paste.
- 2026-09-10 — Fakes prove the logic; only the live host proves the host agrees. Driving
  `POST /precheck` in process against the real graph and the real scratch repo proved the App
  JWT, the installation token and all four Git Data calls in one go, and cost one branch that
  was deleted again. Do this before declaring a seam done, and clean up what it leaves.
- 2026-09-10 — Do not push when pushing deploys and the deploy is half-blocked. Leaving six
  commits local was the right answer: the permission and the deploy belong in one sitting.
- 2026-09-10 — Read the shape from the toolchain, not from memory: `have h : T := sorry` is an
  `Expr.letE` in Lean 4.33, and a theorem's proof term needs `value? (allowOpaque := true)` —
  without it hole extraction silently reports *no holes*, which is the one answer a partial proof
  must never get. Both found by driving a two-hole fixture and looking at the number.
- 2026-09-10 — Lean imports once per process. A second `processHeader` in one run returns an
  environment with no parser extensions, so the second file loses `∧` and `¬` and fails with
  "expected token". A metaprogram over two or three files synthesises one header from the union
  of their imports (`unionHeaderEnv`) — which also lets a partial proof declare the statement's
  own name without colliding with it.
- 2026-09-10 — A criterion can be met by making the thing it describes impossible. F08-AC5 asks
  about a variant labelled `partial` with no `Relation.lean`; F03 had already put the label
  inside that file, so the node cannot exist. Say so in a judgment call and test the two places
  the impossibility is enforced — do not bend the design to make the literal words testable.
- 2026-09-10 — ~~Assert what the API actually lets you control. R2 wants the App as committer;
  the Git Data API fills the committer from the token, so the test asserts the author that *is*
  sent and that no committer field is sent at all. Omission is the enforcement.~~ **Wrong, and
  corrected the same day by the live host — see the entry at the end of this log.**
- 2026-09-10 — Two features can each be the other's dependency and still be buildable: F07-T4
  needs F08-T1, F08 needs F07 for everything else. Take the one task that breaks the cycle rather
  than treating the feature order as a total order.
- 2026-09-10 — An enum value no code can emit is a live bug, not a tidiness problem. `skeleton-hole`
  sat in `graph/v1` and `frontier/v1` because D-25 published it, while D-3 and D-31 said three
  values and called those holes `authored` — so D-25's own worked-example filter was unwritable.
  When two decisions disagree, check whether the *mechanism* exists before choosing a wording:
  here the discriminator D-31 required, the annex citation, had no home in any schema or file
  format, which is why the contradiction had survived.
- 2026-09-10 — Re-price a batching decision before acting on it. Folding D-9's rung rename into
  the same amendment looked free until `back-translated` turned out to be a value in two
  hash-pinned schemas (D-34), which makes a rename a migration. Ask again when the cost you quoted
  turns out to be wrong; the answer changed.
- 2026-09-10 — Sessions can run in parallel on this repo. Mid-plan, another session committed the
  v3.12 rename, D-9's rung and F08-T1 under me, and my just-committed note asserted the opposite.
  Re-read `git log` and `git status` before each commit in a long session, and correct a committed
  record in the next commit rather than leaving it. Two sessions on disjoint files merged fine;
  the collision was in the *claims* the notes made, not the code.
- 2026-09-10 — A hole's type is not a statement. The extractor reported `q` for a hole inside
  `∀ p q, p ∧ q → q ∧ p`, and every child node built from it would have had a `Statement.lean`
  that does not elaborate — D-29's "holes enter the frontier as children" quietly producing nodes
  the gate rejects. Holes now carry `closed_type`, the obligation closed over the binders it sat
  under. When a value crosses from one context into a file of its own, ask what it is closed over.
- 2026-09-10 — Eight red `E`s were one dead Docker daemon, not a regression. `make verify-lean`
  errors at fixture setup when the step-3 image cannot build, which looks like eight failures in
  three files. Read the first error's message before believing the count; start the daemon and
  run `pytest -m docker` alone rather than paying for the 12-minute Lean tier twice.
- 2026-09-10 — A blocker can change identity while you are not looking. F06 waited all morning on
  a GitHub App permission; once granted, the same criterion was blocked by a stale `gate-spec.json`
  pin whose commit predates `gate/precheck/`. Re-derive what a task is waiting on after anything
  external changes, and correct the spec and the index in the same pass — a status note that names
  the wrong blocker is worse than none.
- 2026-09-10 — A re-pin has to reach the thing that reads it. Re-pinning `gate-spec.json` on
  `main` did not help the precheck job at all: a job pins `frontier.json`'s `rendered_from`
  (F06-Q10), checks the graph out there, and reads the network pin from *that* commit. So the pin
  landed first and the products were rendered from it second — the two-commit shape the log
  already recorded, for a second reason. Before re-pinning, ask which commit each consumer
  actually reads the pin from.
- 2026-09-10 — `time.monotonic()` counts from boot on Linux, so a test that ages a cache by
  setting its epoch to `0.0` passes on a laptop up for hours and fails on a fresh hosted runner
  that has been up for twenty seconds. CI caught it; both local tiers were green. Force staleness
  by subtracting the window from *now*, never by assuming the clock's origin — and read a
  CI-only failure as a fact about the environment before assuming flake.
- 2026-09-10 — Omission is not enforcement. The struck-through note above said the
  Git Data API fills the committer from the token, so the test asserted *no committer field*.
  The live host disagreed: it copies the **author** into an absent committer, so the contributor
  was both, and the D-23 split had quietly collapsed. The assertion was asserting the defect.
  Never test that a field is absent as a proxy for what the server will do with it.
- 2026-09-10 — A green run is not a checked run. `smoke_submit` resubmitted the tutorial node's
  committed `Proof.lean` byte for byte, so the pull request was empty, the gate said "nothing to
  gate" and passed — twice, and I wrote both up as AC21 evidence. Read the *run log*, not the
  conclusion. A smoke that drives a diff must assert the diff exists.
- 2026-09-10 — Three of F07's requirements (R7, R9, R10) want an actor that merges or closes a
  pull request, and every mechanism for one needs write permission in a job triggered by that
  pull request — the exact thing C8 forbids, while D-4 forbids the App merging. The classifier
  half landed; the acting half is a new privileged actor on the record repository, which is the
  owner's call. When a spec line implies a permission, price the permission before the code.
- 2026-09-10 — A required status check is matched by exact name, so renaming a CI job silently
  disarms branch protection: the graph's ruleset wanted `gate (steps 1, 2, 4, 5 in the sandbox)`
  and the job had grown into `gate (steps 1, 2 and 4-8 in the sandbox)`, so the check never
  reported and *no pull request could ever merge* — invisible, because a never-reported check
  looks like a pending one. After any job rename, open a pull request and read `mergeable_state`;
  `clean` is the proof, a green check is not.
- 2026-09-10 — Keep GitHub's own review count at 0 and enforce review inside the gate. D-4 v3.11
  makes step 9 a property of the *statement* — a certified statement needs no human — and that
  carve-out is only expressible if the host is not demanding an approval underneath it. Worth
  re-checking whenever the ruleset is touched. (Step 8 is the declared-dep check and always runs;
  step 9 is the human.)
- 2026-09-10 — Naming the App as committer paid twice. Beyond D-23's split it makes a
  pseudonymous submission *attributed*, so the ruleset's
  `require_extra_approval_for_unattributed_changes` does not fire on D-19's account-free path —
  a carve-out nobody had to write. Checked on a live pull request rather than reasoned about.
