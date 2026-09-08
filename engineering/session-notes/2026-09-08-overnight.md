# Overnight build session — 2026-09-07/08

Read this first. It is the record of what the autonomous session did while you slept, what it
decided on your behalf, and what needs you. Everything below is also visible in `git log`
(`F00-Tn:` commits) and `engineering/evidence/F00/`.

## Where things stand

_(the final state is in the last section; this file was updated after each task)_

## Decisions I made for you (review these)

1. **`lean4checker` is deprecated upstream.** Its README says it has been merged into Lean itself
   and ships as `leanchecker` with every toolchain from v4.28.0. The gate calls
   `leanchecker --fresh` from the pinned toolchain; there is no separate lean4checker install.
   Same program, same `--fresh` semantics, one fewer moving part. Logged as F00-Q10 in the spec.
2. **Lean pin: `leanprover/lean4:v4.33.1`**, the latest stable release at session time
   (2026-08-21). In `lean-toolchain`, the fixture graph, the Dockerfile default, and the tutorial
   graph's `gate-spec.json`.
3. **Standalone `uv` installed to `~/.local/bin`** (v0.12.10, official installer, no shell-config
   edits). Your existing `uv` was a pyenv shim from Python 3.11.8 that dies on this repo's
   `.python-version` (`pyenv: version 3.13 is not installed`). `~/.local/bin` is already first on
   your PATH so the new one wins. If you want the old one gone:
   `~/.pyenv/versions/3.11.8/bin/pip uninstall uv`.
4. **elan installed to `~/.elan`** with `--no-modify-path`; the v4.33.1 toolchain under it.
   `make verify-lean` and `pregate.sh` find it via `~/.elan/bin` (config default
   `OPN_ELAN_HOME`); nothing was added to your PATH.
5. **No build backend in `pyproject.toml`** (`[tool.uv] package = false`). The three packages are
   put on the path by pytest/mypy config and by the shell entrypoints. Avoids adding hatchling or
   similar as a fifth dependency (C5). Revisit at F05 when the api needs packaging for Lambda.
6. **mypy runs once per component** (`mypy gate`, `mypy api`, `mypy site`) because the three
   `tests/` directories collide by module name in one run. Test helper modules therefore need
   distinct names across tiers (`gate/tests/fakes.py` is fine; an `api/tests/fakes.py` would
   shadow it).
7. **No `types-*` stub packages.** jsonschema and PyYAML ship no stubs; instead of two more
   dev dependencies the mypy config ignores their imports and `opn_gate.schemas` types its results
   itself. JSON Schema `format` (date-time, uri) also needs extra packages, so the schemas use
   explicit regex patterns instead.
8. **The run timestamp lives inside the attestation's `signature` block.** D-34 requires a
   timestamp and D-5 masks only `runner`, `merge_commit`, `signature`; a top-level timestamp would
   have made two honest runs differ. So `signature` = {kind, key_id, value, timestamp}. Recorded
   as a T3 addendum to F00-Q3. The attestation also carries `graph_commit` (F06 needs it),
   `tooling` {model, harness} (D-23), a per-step `steps` list and `reviewer`.
9. **`toolchain_hash` is nullable** so a step-1 failure still yields a valid attestation.
10. **R19 is implemented strictly**: `Proof.lean` must be `Statement.lean` byte-for-byte up to the
    `:=` of the sorry body, then any body, then the statement's trailing text. Helper declarations
    therefore go inside the body (`have`, `where`, term-mode) — nothing may precede the theorem,
    which is what makes a textual check sound against `open`/shadowing tricks. F01-R4 talks about
    "declarations introduced in Proof.lean"; when F01 adds the Lake package it can relax this with
    an elaborated-type comparison. Worth a look when you draft F01's touch-ups.
11. **`native_decide` is detected from the axiom set**: on v4.33 a proof by `native_decide`
    depends on an axiom named `<decl>._native.native_decide.ax_N`. Step 5 names it as
    `native-decide` before checking the allowlist.
12. **The bounce rule also checks node id and statement hash** of the attached precheck
    attestation (beyond R13's presence, kind and age), so a precheck of some other node cannot be
    reused. It does not verify signatures (D-4: the precheck attestation proves nothing).
13. **The sandbox copies files in and out instead of bind-mounting.** Your Docker Desktop is
    4.12 (2022) on macOS 26 and bind mounts silently show up empty inside containers, even under
    `/Users`. Rather than depend on host file-sharing, `SandboxToolchain` creates a container,
    `docker cp`s the node directory (root-owned) and the work directory (owned by uid 1000) in at
    their host paths, runs one toolchain command, copies the work directory back, and removes the
    container. This also sidesteps uid mismatches on GitHub runners. Isolation flags: `--network
    none`, uid 1000, `--cap-drop ALL`, `no-new-privileges`, pids limit, tmpfs `/tmp`, `--cpus`,
    `--memory` (+ swap = memory), and an in-container `timeout -s KILL` at the graph's wall-clock
    cap. Verified by the docker-tier tests (no network, 30 s cap, no containers left behind).
14. **The gate's wall-clock cap also bounds each toolchain call locally** (pregate). The fixture
    graph's cap went from 30 s to 300 s because a fresh kernel replay of Lean core takes ~40 s on
    your laptop; the 30 s value now lives only in the timeout test.
15. **Sandbox image = elan + one toolchain, nothing else.** Python and the gate stay on the host;
    every toolchain call is wrapped. Base `debian:bookworm-slim` pinned by digest, elan v4.2.4
    pinned by release, toolchain by build arg. ~3.3 GB, builds in ~1 min (mostly the toolchain
    download). Built in CI on every run for now; a registry can come later.
16. **Sandbox `resolve` never installs**: the image holds the pin; `install=True` is ignored.
17. **Attestation ids are 6-digit zero-padded PR numbers** (`attestations/000012.json`), Q8 said
    "zero-padded" without a width.
18. **Signatures are OpenSSH signatures for every kind** (`ssh-keygen -Y sign`, namespace
    `opn-attestation`, over the canonical JSON of the record minus its `signature` block);
    `key_id` is the SHA256 fingerprint. Gate key, precheck key and contributor keys all use the
    same mechanism, so one verifier serves everything.

## Things that need you

1. **Docker Desktop is four years old** (4.12.0, engine 20.10.17). It works for the copy-based
   sandbox but bind mounts are broken and `docker info` panics. An upgrade is worthwhile before
   F10 (devcontainer).
2. **T9 needs a second GitHub identity.** GitHub does not let a pull request's author approve
   it, and D-4 step 9 is a non-author approving review that branch protection enforces. The
   rehearsal PR is authored by your account, so the approval must come from another account (a
   second account of yours, or a collaborator). F00-Q5's "reviewer = founder" reading needs that
   second identity to exist; the GitHub App (F05) will later open PRs on contributors' behalf,
   which is the other way around this. See the T9 section below for exactly where it stopped.
3. **The gate signing key** (C8 item 1): see the T8 section for what was generated and where it
   lives. The private half exists only as the Actions secret; there is no copy anywhere.
4. **Branch protection on the graph repo**: see T8 for what was configured and what the
   post-merge job's commit needs.

## Task log

- **T1 ✓** stack lock in code — `make verify` green in ~2 s (`task-1.txt`).
- **T2 ✓** toolchain pin — `make verify-lean` runs one theorem through the seam: elaborate,
  `leanchecker --fresh`, `#print axioms`; the R16 diagnostic names the install script
  (`task-2.txt`).
- **T3 ✓** schemas v1 — `gate-spec/v1`, `attestation/v1`, `meta/v1`; validation module; pinned
  hashes in `gate/schemas/HASHES` (`task-3.txt`). Note the schemas were still edited during T5
  and T7 (nullable `toolchain_hash`); they are frozen from the moment T8 copies them into the
  graph repo.
- **T4 ✓** layout and step 2 — D-3 validator, permitted paths, statement hash, proof-is-statement;
  the `propositional` fixture graph (tutorial node proven, `and-reassoc`, root
  `and-swap-reassoc` with deps) whose Lean files all compile; twelve adversarial diffs
  (`task-4.txt`).
- **T5 ✓** pipeline and steps 1, 4, 5 — step interface, first-failure runner that turns any
  exception into that step's failure, attestation builder with the D-5 comparison, precheck
  bounce rule with the PR-body block format from Q1 (`task-5.txt`).
- **T6 ✓** `pregate.sh` — CLI, `Signer` seam over `ssh-keygen -Y`, `--sign`; five real-toolchain
  tests including sorry → `sorryAx` at step 5 and a signature that verifies (`task-6.txt`,
  5 min).
- **T7 ✓** step-3 image and `reproduce.sh` — `make verify-lean` runs 14 tests in 9 min: the
  sandbox is isolated (uid 1000, clean env, no resolver), a network-reaching proof fails at
  step 4 naming "no network", a looping proof dies at the 30 s cap, two reproductions of the
  fixture merge commit are byte-identical after masking, `--compare` detects a tampered field
  (`task-7.txt`).
- **T8 ✓** graph seeded and `gate.yml` live — `test_postmerge.py` green; the no-op PR (#1) got a
  green gate run; the seed push's post-merge job correctly found no PR to record (`task-8.txt`).
  Two commits here because the graph must pin a pushed network commit before the workflow can
  run: code first (`a02510c`, then `1e85df2` after fixing an action pin), evidence second.
- **T9** rehearsal — see "Where T9 stopped" below.

## What T8 put on GitHub (review this)

- **Graph repo `thisisanameforsure/open_proof_network_graph`** now holds: `schemas/` (the three
  v1 schemas + `HASHES`, frozen from here on), `keys/gate.pub`, `attestations/`,
  `targets/tutorial/` (gate-spec pinning network `1e85df2`, caps 2 cpu / 4 GiB / 600 s; the
  tutorial node unproved), `.github/workflows/gate.yml`, a README. Two commits, both
  `F00-T8:`-prefixed, pushed to `main` with the admin bypass (the ruleset flags it).
- **Gate signing key** (C8 item 1): ed25519, generated on your laptop into the session
  scratchpad, private half stored as Actions secret `OPN_GATE_SIGNING_KEY` on the graph repo,
  public half committed as `keys/gate.pub` (fingerprint
  `SHA256:XOd3xiS7BYG+uqfTlo5j3uEH96wPy5SCfmBWEsAKZLI`), local copy deleted. Rotation = generate a
  new pair, set the secret, commit the new `.pub` (F00 §7).
- **Ruleset `main: gate + non-author review`** (id 22508489) on the graph repo: PR required with
  1 approving review, last-push approval, stale reviews dismissed, merge commits only; required
  status check `gate (steps 1, 2, 4, 5 in the sandbox)`; no deletion / force-push. Bypass:
  repository admins (you) and deploy keys.
- **Why a deploy key**: GitHub Actions cannot be a ruleset bypass actor on a personal repo, and
  the post-merge job must commit the attestation to protected `main`. So a write deploy key
  (`opn-gate postmerge (attestation commits)`, id 162606490) exists; its private half is Actions
  secret `OPN_GRAPH_DEPLOY_KEY`; the job pushes over SSH with it. **This is a second Actions
  secret beyond the signing keys C8 lists** — logged in the spec as F00-Q11; either C8 gains a
  line or the App (F05) becomes the bypass actor later and the deploy key is removed.
- **Maintenance PRs pass the gate without running it.** `gate.yml` classifies a PR by the node
  directories it touches: none → "nothing to gate" and green (review still required); exactly
  one → the pipeline; more than one → fail. So gate-spec/schemas/workflow changes merge on review
  alone, which is D-35's "visible diff made by the gate owner". A submission is never mixed with
  such changes by the path check.
- **Failed gate runs do not commit an attestation** (the gate job has no write permission).
  The record lives in the run's artifact. D-5's "failed runs publish attestations" needs a
  writer with permission — F03/F07 territory.
- **Action pins**: `actions/checkout@v7`, `actions/upload-artifact@v4`, `astral-sh/setup-uv@v10.0.1`
  (there is no `v10` moving tag; the first runs failed on that, hence the extra commits).

## Where T9 stopped

Done, in a fresh clone of the graph repo (`scratchpad/rehearsal/graph`, since deleted with the
session scratchpad — the branch is on GitHub):

1. `Proof.lean` written for `tutorial-and-swap` (Statement with the `sorry` replaced by
   `intro p q h; exact ⟨h.2, h.1⟩`), committed with a DCO sign-off.
2. `gate/pregate.sh --graph … --node tutorial-and-swap --model claude-fable-5-1 --harness claude-code`
   → all four steps pass, unsigned attestation (`runner: local`).
3. **PR #2** opened: https://github.com/thisisanameforsure/open_proof_network_graph/pull/2 with the
   attestation as the `opn-precheck-attestation` block in the body.
4. The authoritative gate ran on the hosted runner: image built, steps 1, 2, 4, 5 passed in the
   sandbox, precheck block consumed (`signature_kind: none`), `runner: hosted`. 1 m 50 s cold.
   https://github.com/thisisanameforsure/open_proof_network_graph/actions/runs/34188780245
5. `gate/tools/check_reproduce.py` is written (verifies the CI signature against `keys/gate.pub`,
   reruns `reproduce.sh` on the merge commit, compares) but has nothing to check yet.

Blocked on: **an approving review by an identity other than the author.** The PR shows
`REVIEW_REQUIRED`; GitHub will not let `thisisanameforsure` approve its own PR, and the ruleset
requires one approval (D-4 step 9). Nothing in the protocol or the tooling can get past this — it
is the one human act, by design.

**To finish T9 (about 10 minutes of your time):**

1. Approve PR #2 from a second GitHub account with write access to the graph repo (invite it as a
   collaborator first), or have a collaborator approve. Then merge with a merge commit (the ruleset
   allows only that method; "Merge pull request" button).
2. The `postmerge` job runs on the merge: re-derives the verdict in the sandbox, records the
   reviewer, signs with the gate key, pushes `attestations/000002.json` to `main` via the deploy
   key. Watch it at https://github.com/thisisanameforsure/open_proof_network_graph/actions.
3. On your laptop (Docker running):
   ```
   git -C ../open_proof_network_graph pull
   uv run python gate/tools/check_reproduce.py 000002 > engineering/evidence/F00/task-9.txt
   ```
   Exit 0 means the CI signature verifies and the local sandbox reproduction is identical modulo
   the masked fields. Commit that file as `F00-T9: rehearsal — …`, set the ledger to
   `T1–T9 ✓`, tag `F00-done`, and F00 is complete.

If the post-merge job fails, its log will say why; the likeliest culprits are the deploy-key push
(ruleset bypass) and the `sign` step (secret name `OPN_GATE_SIGNING_KEY`). Both were tested
locally with throwaway keys but not on GitHub, because no PR could merge without the review.

## Where things stand (final)

- **F00: T1–T8 done and verified, T9 blocked on the human step.** Nine `F00-Tn:` commits here,
  three in the graph repo, all pushed. Ledger: `T1–T8 ✓ 2026-09-08 · T9 in progress`.
- **116 tests**: 102 fast (`make verify`, ~2 s, the pre-commit hook), 14 real-tier (`make
  verify-lean`, ~10 min on your laptop: 8 need elan, 6 need docker).
- **CI on this repo** (`ci.yml`): fast tier green; the real tier was still running at the end of
  the session (it builds the sandbox image and installs the toolchain cold each run).
- **Uncommitted**: nothing in code. This notes file and the `engineering/CLAUDE.md` state update
  are committed with the T9-in-progress commit.
- Nothing was deleted, force-pushed, or changed outside the two repos, `~/.local/bin/uv`,
  `~/.elan`, and the Docker image `opn-gate:leanprover-lean4-v4.33.1` (3.3 GB; `docker rmi` it
  whenever).

Spec items worth your eyes when you have a minute: F00-Q10 (leanchecker), the Q3 addendum
(timestamp inside `signature`), Q11 (reviewer inheritance; deploy-key secret vs C8). None of them
overturn a D-number; two of them nudge C8 and F01.
