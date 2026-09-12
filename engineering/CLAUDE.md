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
  earlier, so `trust_base` became v3, logged as F02-Q5; paid again 2026-09-11 when F11-R12 named
  `targets-index/v2` a day after F07-R8 shipped one, F11-Q9). Specs should say "the next
  version", and the check is one `ls gate/schemas/<name>/` before a requirement names a number.
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
- 2026-09-10 — Omission is not enforcement. A note written that morning said the Git Data API
  fills the committer from the token, so the test asserted *no committer field*.
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
- 2026-09-10 — The sandbox holds only the node under check and the work directory. Admission's
  relation check read the *root's* `Statement.lean` from the graph tree, passed every laptop
  tier (AC18 included) and failed on the first sandboxed run with a bare "does not elaborate".
  A check that reads a sibling node must stage it into the work directory first; and any check
  that will run in the sandbox deserves one docker-tier test before it is called done.
- 2026-09-10 — A new gate flag would have blocked every merge. `classify --author` was the
  natural shape for F08-R8, but the graph pins a commit that does not know the flag, so the
  workflow passes the author as `OPN_PR_AUTHOR` (the `OPN_RUNNER` precedent) and reads every new
  classification field with a default. The `gate.yml` change is then inert on the old pin and
  can be committed to the graph before the re-pin, instead of waiting uncommitted for it.
- 2026-09-10 — Test the shape that lands, not the shape that is built. `scaffold.files` returns
  paths relative to the node directory and the service pushed them bare, so the first proposal
  would have put `Statement.lean` at the graph root. The test that caught it materialises the
  pushed files as a tree and runs the gate's own layout check and classifier over them; a test
  that only read the dict would have passed.
- 2026-09-10 — A fake elaborator cannot see a name clash. Consolidation's probe re-declared the
  theorem it imported, because duplicates share a name; every fast-tier test passed and the
  first real-toolchain run failed. Any probe that imports the thing it is compared against
  needs its own declaration name — and one lean-tier test per new Lean-facing seam, always.
- 2026-09-10 — Price a notation before adopting it as an identifier. D-8's `<id>@v2` would have
  bumped six hash-pinned schemas; read as notation (the way F03 read D-13's `d13/v1`) and spelled
  `<id>-v<n>` with `supersedes` in `meta/v4`, it cost one field. Recorded as F08-Q16 with the
  reversal path, and the doc gets a notation note rather than an overturn.
- 2026-09-10 — A failing-case sweep (453 → 1232 fast tests, 91% → 99% branch, all in
  `engineering/session-notes/2026-09-10-test-coverage-review.md`) found 22 defects, none by a
  happy-path test. Three shapes recur and are worth checking in every new module: a substring
  heuristic standing in for a fact (`"sorry" in witness` reads the slot's own comment, so a
  filled witness stays blocked and can be filled twice); a mode's allowed roles wider than its
  requirement (a listed curator's diff may replace an existing witness unchecked); and
  exceptions escaping `cli.main` after the expensive work is done (`main` catches two error
  types; nine other commands leak `SchemaError`, `FileNotFoundError`, `SandboxError`).
  Each defect is a strict xfail, so fixing one flips a test red until the mark comes off.
- 2026-09-11 — Git exports `GIT_DIR` and `GIT_INDEX_FILE` to hooks. Run from a linked worktree,
  the pre-commit hook's suite made the curator `--branch` tests act on the *network* repo:
  `checkout -b curator/revise` and a whole tree staged as deleted, in two worktrees at once,
  because `cli._git` inherited the environment. Any child `git -C <elsewhere>` must scrub the
  repo variables (`config.child_environment(drop=GIT_REPO_VARIABLES)` now does; the hook unsets
  them too). Recovery: `git symbolic-ref HEAD refs/heads/<branch>`, `git reset` (mixed), delete
  the stray branches; the working tree survives.
- 2026-09-11 — The sweep's defects landed as three spec tasks (F08-T7, F05-T6, F04-T7) plus the
  F11/F12 spec edits; every xfail came off except two that are real and out of scope: float
  parity at the store seam, and admission not seeing a proposal that redeclares an existing
  node's theorem name (lean tier, F08-Q18). Both are held strict, so they cannot be forgotten.
- 2026-09-10 — Naming the App as committer paid twice. Beyond D-23's split it makes a
  pseudonymous submission *attributed*, so the ruleset's
  `require_extra_approval_for_unattributed_changes` does not fire on D-19's account-free path —
  a carve-out nobody had to write. Checked on a live pull request rather than reasoned about.
- 2026-09-11 — An SDK's auth switch gates its transport, not its tools. The MCP SDK's
  `AuthSettings` answers 401 to `initialize` and `tools/list` without a bearer, which is the
  opposite of D-28's "reads unauthenticated, writes token-authenticated"; the fix was to keep
  the SDK's verifier protocol and bearer backend and put the gate inside each write tool, which
  also gave every refusal the tool's own structured shape (F09-Q6). Read the middleware, not the
  README, before adopting a framework's auth flag.
- 2026-09-11 — Re-price a spec's file list against the registry it names. F09-T2 put twenty-one
  adapter result schemas in `gate/schemas`, whose id grammar is one level and whose index every
  F03 golden carries; they went beside the adapter instead (F09-Q5). The SDK had also moved:
  2.x depends on `httpx2`, so the spec's "1.x line" was a real constraint, not a formality.
- 2026-09-11 — The founder's laptop is a deployment target. With `.env` sourced, the local runner
  talks to the real graph and the real scratch repository, so a network-tier smoke can run
  unattended before any push: the tutorial precheck minted a token in 138 s, every read crossed
  the live host (the new `list_dir` included), and Claude Code itself was the client through
  `claude mcp add --transport http`. Only the deploy and a claimable node remain the owner's.
- 2026-09-11 — A deploy check that cannot import the package still has to see the package. Two
  deploys in a row failed on the MCP adapter: the new package check imported `opn_api` with only
  `gate` on the path, and then the function itself died at import because the build stripped
  every `dist-info` and the SDK resolves its version through `importlib.metadata`. Neither the
  fast tier nor the local runner could see either: both run from the venv, where metadata exists
  and paths are set. Rehearse the build step locally (`uv pip install --python-platform
  aarch64-manylinux2014 --target`) and check the package on disk before a push that deploys.
- 2026-09-11 — The first live merge of a new node kind finds what fixtures cannot. A D-30
  variant has no dependents, so the first merged variant gave the DAG two sinks and F03's root
  inference refused; the products stopped rendering until the curator declared the root by pull
  request (a direct push does not trigger the post-merge job). And a post-merge run that fails
  before its ledger step loses that line for good, because a re-run checks out the same merge
  commit. Before the first live use of any new mode, ask what the post-merge job assumes about
  the tree — and match a run to the commit it is for, never to "the latest completed run".
- 2026-09-11 — Docs are tests, and the test found the doc's own bugs. AGENTS.md's 28 commands run
  against a fixture clone and the fake service on every `make verify`; the first run caught
  compact JSON (`"ok":true`, not `"ok": true`), locale-dependent `sort`, and a `cd` that did
  not survive a fresh shell. The runner carries variables across blocks with `set -a` plus an
  `env -0` dump, so a document reads like a pasted session. Tag the two blocks a fixture cannot
  absorb (`sh manual`) and freeze that set in the test, or commands hide behind the tag.
- 2026-09-11 — A pin four files must agree on is a pin one function should read. F10-R5 wanted
  the image digest in gate.yml, the precheck workflow, reproduce.sh and devcontainer.json;
  `ensure_image` reads `devcontainer_ref` from the spec instead, so the three scripts name no
  image at all and the test asserts *that*. Same shape as the network pin: one visible diff.
- 2026-09-11 — `uv run` inside an image synced with `--no-dev` tries to install the dev group
  and dies offline; set `UV_NO_DEV=1` in the image (and `UV_CACHE_DIR` somewhere writable for
  uid 1000). Found by the docker-tier test, not by the build, which succeeded.
- 2026-09-11 — A deploy window is a design input. `get_node` serving `CONTEXT.json` would have
  gone dark between the api deploy and the graph re-pin that first writes the file; the
  generator reads through a seam and the api derives the same document from the host until the
  file exists, and AC4's test is the equality of the two. Ask what the tool does on the day the
  push lands, not only after.
- 2026-09-11 — A cache must be invisible to the attestation. D-5 says two runs anywhere agree byte
  for byte; whether a dependency's olean was fetched or compiled is not a fact about the tree,
  so hits go to the printed summary and `cache.json` only, and the lean-tier test asserts the
  attestations with and without the cache are identical. `leanchecker --fresh` re-checks every
  import, which is why a poisoned cache can waste time but never change a verdict.
- 2026-09-11 — `aws cloudformation deploy` cannot say "keep the previous value"; a stack whose
  domain and certificate were set at deploy time would have lost them to the template defaults.
  Build a change set with `UsePreviousValue` for every existing parameter, read it, then execute.
- 2026-09-11 — A one-field schema bump reaches every consumer, and the consumers are not where you
  would look. `frontier/v2` (one boolean, D-33 dormancy) touched the api's `/frontier.json` route,
  the MCP field filter, both smoke tools, the deploy workflow's package check and the site's
  accepted-versions map. Grep for the *version string*, never for the module, and budget the sweep
  into the same commit as the schema. What scales is a set per product rather than a pin: the site
  already did it that way and was the only consumer that needed no thought.
- 2026-09-11 — A derived value with two writable homes will disagree with itself, and the wrong one
  will be the one a human edited. F11-R1 listed `fidelity` and `claimable` among `target.yaml`'s
  fields while R3 and R4 derive both; the record now carries only the inputs and
  `targets/index.json` carries the outputs with their reasons (F11-Q10). When a spec lists a
  derived field on a record, settle which of the two is the source before writing the schema.
- 2026-09-11 — A requirement to *show* something can be a change to a checker rather than to a
  page. F11-R10 wants the Targets page to link a target's upstream source; F04-R13's link checker
  refuses every off-site link and would have failed the build. Loosening the rule was the wrong
  fix — `links.check` now takes an allowlist built from the *validated* target records, so the
  renderer still cannot invent an outbound link (F11-Q11).
- 2026-09-11 — Read the first error, not the count, in a fresh container. Sixty-seven errors and
  nine failures across the gate and the api were one missing `ssh-keygen`: the signer shells out to
  it, and every test that signs or verifies died at `FileNotFoundError`. `apt-get update` then
  `apt-get install openssh-client` fixed all of them.
- 2026-09-11 — A test that borrows the developer's machine is green locally forever and red in CI
  forever. Three `--branch` tests had been failing on `main` for a week: `--branch` commits with
  whatever identity the environment carries, because the gate deliberately fabricates none
  (F08-Q17), and a hosted runner has no `~/.gitconfig`. Reproduce a CI-only failure by taking the
  ambient thing away — `HOME=/tmp/empty uv run pytest` found it in one run — and have the test
  supply what it needs instead of inheriting it.
- 2026-09-12 — Two green branches can merge into a broken one, and only the type checker sees it.
  A session on a phone built F11 from a commit that predates F10, so F10 changed `ensure_image` to
  take the whole gate-spec (R5's pinned digest) while F11 wrote a new caller against the old
  signature. Both branches passed everything they had; git merged the two files without a
  conflict, because neither side edited the other's line. `mypy --strict` caught it in one run.
  After any merge of parallel sessions, run the type checker before believing the test count —
  and look first at the functions whose *signature* one side changed, since a signature is the one
  edit whose blast radius is entirely in files it does not touch.
- 2026-09-12 — The 25-Fields-medallist declaration (2026-09-11) condemns "the mass production of
  'true/false' statements" on open problems, and D-6's first-priority source is the Erdős list
  chosen for its "demonstrated resolution regime" — as written, the mission is the condemned
  activity, and the people D-22 recruits are the signatories. Researched in
  `docs/research_digestion_2026-09.html`: the protocol already answers most of Leiden (public
  failures, human credit, no leaderboard, prior art, report-back) but digestion is optional and
  unstated. Proposed amendments A1–A5, the load-bearing one being a named digester at intake
  (D-32's writer appointed at listing, not at resolution). Two things the evidence killed: AI-drafted
  proof sketches as a rung (Tao: they "obscure the most interesting portions") and any readability
  metric (none is validated). Explainers already exist as a gate mode; what is missing is a
  signature and a status. Mike's calls: proofs-first vs digester-first, and whether Erdős
  problems stay first priority.
- 2026-09-12 — A defect held because "no fake can see it" was worth re-reading before fixing. F08-Q18
  parked the theorem-name clash in the lean tier on the grounds that only the real elaborator could
  show it. But the fix is a string comparison over sibling `Statement.lean` files — no toolchain at
  all — so the fast tier covers it after all, and the lean test became an ordinary test rather than
  the only one. When a held defect names the *reason* it is held, check that the reason still
  applies to the fix you are about to write; it constrains the test, not the code.
- 2026-09-12 — Both halves of a seam must agree on what is *unstorable*, not just on what round
  trips. `plain()` had turned DynamoDB's Decimals back into JSON numbers since F05, but nothing did
  the reverse, so a float was a `TypeError` on DynamoDB and a happy write in memory. The parity
  tests had been driving DynamoDB alone; driven through the shared both-stores fixture they are
  parity tests, and that is the shape to reach for whenever a seam has two implementations.
- 2026-09-12 — A proof cannot add an import. F00-R19's proof-is-statement check compares the
  header too, so the first on-ramp fixture failed step 2 on `import Mathlib.Tactic.Linarith` in
  the proof. R7's "provers may use Mathlib beneath the local definitions" is a property of the
  *statement*: the curator seeds each statement with the imports provers may draw on, and every
  elaboration pays for them (F11-Q16). Decide the import set with the timing in hand.
- 2026-09-12 — Read the checkout, not the manifest. "Every Mathlib package has built oleans" was
  true of seven and false of `Cli`, a build-time dependency of the cache tool, and the rule
  refused a real 6.8 GiB checkout at step 1. Require what is imported (Mathlib's own lib) and
  take whatever else is there.
- 2026-09-12 — A Mathlib image is a disk event. Two builds died mid-download with "Bad response
  from Docker engine"; the cause was the laptop's data volume at 198 MiB free (Docker.raw grows
  and never shrinks on its own; the checkout is 7 GiB; a second copy lives inside the image).
  Check `df /System/Volumes/Data` before a multi-GiB build, and expect the docker tier for a
  Mathlib graph to belong to CI unless the laptop has ~20 GiB spare (F11-Q17).
- 2026-09-12 — A smoke's heuristic drifts when the shape it checks changes. F09's MCP smoke flagged
  any `.text` as prose; F10 put the statement's Lean source at `$.context.statement.text`, the
  fast tier's demarcation tests learned the new shape, and the smoke did not — so the first
  deploy after the merge went red on a check the tests had already passed. When a bundle's
  shape changes, grep the smokes for the field names as well as the tests.
- 2026-09-12 — "Built as pure functions; nothing invokes them" is a status that hides a missing
  mode. F07 shipped partial mode's classifier, artifact rule and post-merge effects as tested
  functions with no dispatch, and F11-R8's "skeleton submitted through F07" read as done work
  until the first partial hit step 2's `proof-missing`. When a feature's ledger says a piece has
  no caller, the next feature that depends on it owns the caller — price that before promising.
- 2026-09-12 — A check that needs a later step's build is that step's last word, not a step of
  its own. The artifact rule numbered 4 beside the replay duplicated D-4's numbering and broke
  every consumer of the attestation's step list at once. The verdict's steps are the protocol's
  list; anything else rides as a step's diagnostic.
- 2026-09-12 — A hole inherits the holes before it: the extractor closes each `have`-bound hole
  over the binders in scope, and an earlier hole is one. Order a skeleton's lemma holes before the
  assembly's locals, and expect each child to carry its predecessors as hypotheses (F11-Q22).
- 2026-09-12 — A test that "modifies" a merged file to set up a submission is testing a refusal.
  The apply tests failed with `path-forbidden` twice — once for deleting Proof.lean in the same
  commit as the assembly, once for editing the statement's imports in a later one — because the
  gate correctly refuses both. Put the tree's pre-conditions in the base commit and only the
  submission in the diff; the refusals were right.
- 2026-09-12 — The sandbox seam moves *processes* into the container, not Python's file reads.
  Step 1's Mathlib check verified the checkout with `Path.is_file()` and passed every laptop
  tier; in CI the image carried the checkout and step 1 said it did not exist, because the
  reads looked at the host. Anything the gate learns about the image's filesystem has to come
  back on a process's stdout (`SandboxToolchain.resolve` now probes with one `sh -c`). The
  third time a check that reads a path outside `_exec` has failed only in the sandbox
  (F06-Q6, F08-Q13): treat a host-side `Path` in sandboxed code as a bug on sight.
- 2026-09-12 — A registry's `answer(sorry) ↔ P` is a question, not a proposition; the graph's
  statement is P. Formal Conjectures' own docstring says the answer needs a mathematician, which
  is what D-9's QA record supplies; the negative answer has a home in D-12's counterexample. The
  licence gate earned its keep on the first run: one file's header said 2026, the adapted
  statement had copied 2025, and the import was refused by name (F11-Q24).
- 2026-09-12 — "Rebuildable" for a source the network may not republish means the *command*
  that fetches it, not the file. The seed pass's inputs include one erdosproblems.com page per
  problem and the site states no licence, so the dataset is committed (extracted from the
  report) and the pages are named as fetches (F11-Q23). R10's rule reaches the repository.
- 2026-09-12 — A rehearsal that reports READY with steps skipped is lying by omission. The
  first live `rehearsal.py` run skipped four of R11's steps for want of inputs and printed
  READY, because the verdict only knew *failed* and *pending*. Every "all steps pass" tool
  needs a third state for "not attempted", and it must count against the verdict. Also: the
  live frontier was not empty as the notes said — F08's merged variant is claimable — so a
  read-only probe became two live pull requests; re-read the frontier before assuming a run
  writes nothing, and clean up what it opens (both closed, branches deleted).
- 2026-09-12 — The first merge of a new mode found two refusals no fixture had: an intake staged
  as one five-target branch cannot pass the gate, because the workflow takes exactly one target
  per pull request and `THIRD_PARTY_NOTICES.md` is a path no submission may touch — and both
  refusals were right. Split it into five pull requests and push the owner's file with the re-pin
  (F11-Q26). Before staging a branch for a mode's first live use, run `classify` over a worktree
  of it with the gate you are about to pin; it takes a second and would have said so a day earlier.
- 2026-09-12 — The first live skeleton failed on an import the fixture had supplied by accident.
  The live on-ramp root imports `Defs.IsPrime`, `Mathlib.Tactic` and an empty Context; the fixture
  root has a proved dependency whose Context imports `Defs.Fact`, so the skeleton's `Opn.fact`
  resolved in every test and nowhere live. A proof cannot add an import (F00-R19), so the
  skeleton moved to `Nat.factorial` (F11-Q27). When a fixture has more structure than the live
  object it stands for, its passes are worth less than they look; keep one fixture with the live
  shape — here, a root with no dependencies.
- 2026-09-12 — A step's output can duplicate its input once the input moves. F07's post-merge
  filed a merged partial under `attempts/`; F11 made the submission *be* an `attempts/` file, and
  the first live merge filed the same text twice (F11-Q28). The fixture hid it because the test's
  file was named for a different pseudonym than the block's. When a later feature changes where a
  thing arrives, re-read every step that records where it went.
- 2026-09-12 — The strict up-to-date ruleset turns N pull requests into N sequential rounds, each
  re-building the Mathlib image (~6 min) — an hour for five targets. And a pull request that is
  BEHIND fails the gate's "one target" step, because the workflow diffs from the pull request's
  stale base rather than the merge commit's first parent. Publishing the image (the tag, F10)
  and diffing `HEAD^1` are the two fixes; both are for the next sitting.
- 2026-09-12 — A fixture helper that adds a variant re-finds F08-Q19 every time: a `related`
  variant has no dependents, so the DAG has two sinks and root inference refuses. The helper
  declares the root in a `target-status/v2` record now; any fixture that grows a sink must.
- 2026-09-12 — Record the recipe that made a fixture, not just the rule that it came from the
  gate. F05-Q5 says the api's `targets-index-listed.json` is a golden copy; nothing said how, and
  regenerating it at v4 took three tries to rediscover (the root directory renamed to
  `listed-lemma` with its `META.yaml` id, `take_in` with `root_dir`, `rendered_from` of forty
  5s, `commit_time` 2026-09-09T12:00:00Z). Equality of every pre-F12 field was the check that
  the recipe was right; the recipe is now in `engineering/evidence/F12/task-6.txt`.
- 2026-09-12 — A page can hide what a test asserts. The QA table carried twelve columns and its
  wrapper scrolls, so the pass state and the signers were off-screen while the string assertions
  passed; the screenshot caught it. Visual evidence is a check on layout, not a formality — look
  at it before writing it up, and put a wide table's per-row verdict under the table.
- 2026-09-12 — A container without elan or docker cannot run the lean tier, and the ledger must
  say so rather than ✓: T2 and T4 shipped as "built, lean tier pending CI" with the run ids
  recorded once green. A `FakeToolchain(raise_on="elaborate")` also showed that a toolchain
  error inside `StatementStep` escaped the screen; AC18 wanted an `inconclusive` compile row,
  which is what a screen must answer when it cannot run at all.
- 2026-09-12 — The watcher's write access is a fourth secret door (F12-Q16), the model's key a
  fifth (`OPN_MODEL_API_KEY`), and neither existed in the build. Both workflows run in the mode
  the missing secret allows — the watcher dry-runs and keeps its report; the model commands
  refuse with a named error — so a missing permission never reads as a passing run.
- 2026-09-12 — A tag is a release, and the first one finds what nothing has run. The first tag
  push this repository ever made published no image: `tr -c 'A-Za-z0-9_.-\n' '-'` reads `.-\n`
  as a reverse range on GNU tr and is accepted silently by BSD tr on the laptop, so no local run
  and no static read of the file could tell the two apart. The second attempt built and pushed,
  then went red on its own in-image check, which imported `opn_gate` without `PYTHONPATH` — the
  image was right and the check was wrong, because this project installs no package and every
  entrypoint puts it on the path itself. Both fixed; the guard that covers the class is asserting
  the expression uses no external program, not asserting its output.
- 2026-09-12 — A node the gate itself creates must still pass the gate. The post-merge job writes
  a hole's `Statement.lean` from the assembly and its `META.yaml` by bot, and neither ever meets
  step 6: three of the on-ramp's four holes carry `2 ≤ m`, `off-by-one-range` flags it, nothing
  wrote `acknowledged_hazards`, and so admission refuses *every* submission against those nodes —
  while `POST /proposals/witness` pushes `Witness.lean` alone and cannot supply the cure
  (F07-Q19). Whenever a job creates a record on the graph, run the gate's own checks over what it
  wrote, not only over what a contributor sends.
- 2026-09-12 — A merged partial derived its parent `proved` and the target `resolved`, so the
  public site said Euclid's theorem was resolved with four blocked holes and no `Proof.lean`
  anywhere (F03-Q7). The attestation for a partial is a passing attestation against the parent's
  statement hash and says nothing about which artifact it was; `artifact_of` answers `None` for a
  node with no proof file and the caller defaults that to `"proof"`. The suite agreed because no
  test had ever attested a node whose proof file was absent — the state a merged partial leaves
  behind — not, as this entry first said, because the fixture lacks `Proof.lean` files (it has
  them; the expected-failure test written that evening was failing on its own guard, and was
  rewritten with the fix). Fixed the same day on Mike's rule: proved needs a formal statement
  *and* a valid proof in the tree. Test the state a mode leaves behind, not only the mode.
- 2026-09-12 — A checker that regenerates must run from the commit that generated. Run from
  `main`, `check_products.py` reported nine differences on a healthy bot commit; every one was
  F12's schema bump (`graph/v2→v3`, `targets-index/v3→v4`), because the tool regenerates with the
  tooling it is run from while the products were rendered by the pinned gate. Run from a worktree
  at the pin: `{"ok": true, "problems": []}`. The tool should say which gate it is using before it
  reports a difference.
- 2026-09-12 — The toolchain answers questions memory cannot. The four hole witnesses were checked
  before submission by running the gate's own `opn-witness-type` over a Mathlib-free mock of the
  four statements — expected type, definitional equality and the axiom set, all on a laptop with
  no Mathlib checkout — and the live gate then printed `expected` and `witness` identical to the
  mock's. Writing the witnesses in Lean core only is what made that possible, and it also means
  they cannot break under a Mathlib rename. The same mock caught a parse error (two doc comments
  before one declaration) before any pull request existed.
- 2026-09-12 — A witness for a later hole is real mathematics, not a token. A hole inherits its
  predecessors as hypotheses (F11-Q22), and step 7 asks for the hypotheses closed over their
  variables — so witnessing h3 and h4 meant proving that every m ≥ 2 has a prime divisor and that
  nothing but 1 divides two consecutive numbers. Budget for that when a skeleton's holes are
  ordered: the last hole's witness costs as much as the lemmas before it.
- 2026-09-12 — Read an image's labels from the registry, not by pulling it. `pin_image.py --verify`
  pulls, and a Mathlib image is 3.5 GiB compressed against 6.6 GiB free, so the check it exists to
  make is unrunnable on the founder's machine. The labels live in the config blob: a pull token,
  the manifest by digest, the blob — a few kilobytes and no disk.
