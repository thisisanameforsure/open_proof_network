# Orchestrator log — live tester, infinitude-of-primes (2026-09-13)

## Baseline (before the tester wrote anything)
- Graph main `6486959`. Euclid root `infinitude-of-primes` blocked on deps h1–h4; holes `ready`, origin `skeleton-hole`.
- Target `euclid-primes`: status `listed`, fidelity `mechanical-only`, posting null,
  `not_claimable: [status-listed, grade-below-screened-and-signed, no-posting]`. So nothing on it is claimable.
- Committed frontier (`frontier/v2`, rendered_from `e559deb`) and api frontier both: holes h1–h4 `claimable: false`,
  claims history 0, attempts 0; root absent (blocked).
- Site root node page: "blocked on a dependency", "No proof merged yet", "No attestation", 1 annex.
- Snapshots in `baseline/`.

## Events
- 19:31 UTC — graph PR #34 `proof: infinitude-of-primes--h1`, one file `nodes/infinitude-of-primes--h1/Proof.lean`,
  author `app/open-proof-network`. Gate run 34777912609 FAILED at workflow step 7 "Step 9 — a non-author approving
  review" before any sandbox step (known finding 7 of 2026-09-13, still unfixed). Lean: `Nat.dvd_factorial` unpacked
  into `Opn.Divides`.
- Approved #34 as `thisisanameforsure` to satisfy step 9. Review-event run 34777962943 green; verdict steps
  1 toolchain, 2 paths, 4 kernel-replay, 5 axioms, 6 hazards, 7 witness, 8 deps all `pass`; olean cache hit.
- BUT `mergeable_state` stayed `blocked` with the approval in and a green run: the rollup holds the stale
  `pull_request`-event FAILURE and the `pull_request_review`-event SUCCESS under the same required check name.
  A contributor's valid PR needs a human to *re-run* the failed run as well as approve (new observation,
  sharpens finding 7). Re-ran 34777912609.
- 19:30:47–19:33:04 UTC — tester opened #35 (h2, strong induction via `Nat.strongRecOn`), #36 (h3, `Nat.dvd_add_right`
  + `Nat.dvd_one`), #37 (h4, `Nat.factorial_pos`), one `Proof.lean` each; all red at step 9 within seconds.
  Four PRs in ~2.5 minutes = four sequential merge rounds under the strict up-to-date rule.
- Re-run of 34777912609 (attempt 2) green → `mergeable_state: clean`. Merged #34 at 19:53:45 UTC, merge commit `a9f1090`.
  Waiting for the `gate: #34 pass` bot commit before updating #35.
- #34 merge commit `a9f1090` (parents 6486959, ca6c58c) touches exactly the one Proof.lean. #35–#37 unchanged.
- From the tester's own writes log (peeked, not interfered with): MCP precheck worked with a token this time;
  `claim_node` on h1 → 409 node-not-claimable; two root proofs prechecked: **A = assembly over the holes**,
  **B = direct proof using no hole** — both fail step 4 `dep-unproved`. For B that is questionable: a proof that
  references no dependency is refused because the node's declared deps are unproved. Check in analysis.
  Also saw a stray `node-not-in-frontier: infinitude-of-primes is not in the frontier` 404 in its log.
- 20:02:12 UTC bot commit `f345529 gate: #34 pass` (author opn-gate), ~8.5 min after the merge. 26 files:
  attestation `000034.json` (verdict pass, trust_base kernel, review pr-approval by thisisanameforsure, steps 1,2,4–8 pass),
  h1 META/graph → `proved`, h1 CONTEXT proof present/artifact proof, h1 dropped from frontier.json, index proved 1 / ready 3;
  every other target's graph.json + CONTEXT.json churned (rendered_from only). Root stays `blocked` (3 deps unproved).
- Attestation record gaps to check: `submitter: null`, `precheck_attestation.hash: null` though the tester passed a
  precheck id, `model_and_tooling: undeclared`, `tooling {harness,model}: null`.
- CONFIRMED record gap: PR #34 body carries `submission-meta/v1` with pseudonym `euclid-tester-7c2`, tooling
  model `claude-opus-5`, harness, precheck_job_id `01M2E3DB606BCKJH3Y9MMYXFR3`, plus the service-signed precheck
  attestation. Commit author = pseudonym, committer = App, DCO sign-off (D-23 split OK). Yet merge attestation 000034:
  submitter null, tooling null, model_and_tooling "undeclared", precheck_attestation.hash null. Declared data dropped.
  Oddity: submission identity `proof_kind: "tutorial"` on a non-tutorial node (how the token was earned).
- Site h1 page at f345529 by ~20:10: `proved`, proof commit a9f1090, attestation 000034, reviewer shown; no submitter shown.
- Timing correction: at 20:04:44 (2.5 min after bot commit 20:02:12) the site home, h1 page and frontier page were
  already at f345529 (h1 dropped from the site frontier); api `/frontier.json` still `rendered_from e559deb` listing h1.
  Background poll measures when the api catches up.
- Api `/frontier.json` moved to `rendered_from a9f1090` at 20:06:39 UTC: ~4.5 min after the bot commit (20:02:12),
  ~13 min after the merge (19:53:45). Site was ~2 min faster than the api.
- Api frontier vs committed `frontier.json` at f345529: same rendered_from (a9f1090), same entry set (euclid h2–h4),
  every field equal except `tutorial/variant-93e79cb5` claims.history_count committed 0 vs api 6 — the unset
  `OPN_API_CLAIMS_URL` finding from the last live test, still live. Confirmed 20:07 UTC: graph repo variables are
  only OPN_AWS_REGION, OPN_CACHE_BUCKET, OPN_CACHE_PREFIX, OPN_CACHE_UPLOAD_ROLE_ARN.
- Frontier `attempts: 0` everywhere although the tester ran two failed root prechecks (prechecks aren't attempts?).
- ROOT CAUSE (submitter/tooling null): graph `gate.yml` postmerge fetches the PR body only
  `if: steps.classify.outputs.mode == 'partial'`, and passes `--pr-body-file` only in partial mode. A proof merge's
  attestation is built with no submission block → `submitter_of(None)` = null, tooling "undeclared".
- Site Contributors page at f345529: "No ledger files exist yet: nothing has been credited." after merged partial #33 and
  proof #34. gate.yml runs `opn_gate.cli ledger` only when `mode == 'proposal'` (F08-R13 statement line); ledger.py's
  docstring says every merged proof earns a `proof` line (F07-R12). CONFIRMED: `ledger.proof_entry` and `ledger.postmortem_entry` have NO production callers (only
  gate/tests/test_ledger.py); the only `ledger.record` call is the proposal statement line (cli.py:2005). So no merged
  proof, partial or postmortem has ever credited anyone — the Contributors page is empty by construction.
- Site euclid target page at f345529: dependency graph and node table agree with graph.json (h1 proved, h2–h4
  "ready to prove", root "blocked on a dependency"). Cosmetic: every hole's graph label is truncated to the same
  "infinitude-of-primes-…", so the four holes are indistinguishable by label (only the title text differs).
- #35 update-branch → head `74e9560`; approved that head immediately. Two runs: `pull_request` 34779529038 (20:02:52)
  and `pull_request_review` 34779533023 (20:02:56); both still building at 20:07:56, so the synchronize run passed
  step 9 — approving within ~3 s of the update-branch avoids the stale red check. Two full sandbox builds per round.
  Both runs completed success; `mergeable_state: clean` with no re-run needed. Merged #35 at 20:13:35 UTC, merge
  commit `b134abc` (parents f345529, 74e9560) touches exactly h2's Proof.lean. Waiting for `gate: #35` bot commit,
  then `round.sh 36`.
- 20:24:28 UTC bot commit `ef04537 gate: #35 pass` (~11 min after merge). graph.json: h1, h2 proved; h3, h4 ready;
  root blocked. Attestation 000035: pass, kernel, review pr-approval by thisisanameforsure, merge_commit b134abc,
  and again submitter null / model_and_tooling undeclared / tooling null. Still no `ledger/` in the tree.
  Site at ef04537 by 20:25:11 (≤43 s after the bot commit): h2 page shows proof commit b134abc, attestation 000035.
  Api `/frontier.json` at `rendered_from b134abc` by 20:25:39 (≤71 s after the bot commit), euclid entries h3, h4 only.
  So the h1 round's 4.5-min api lag was the cache window, not a fixed delay: this round it was under 72 s.
  Started `round.sh 36`: #36 was behind_by 7; update-branch → head `8bf2333`; approved. Both runs success, no re-run,
  `mergeable_state: clean`. Merged #36 at 20:35:59 UTC, merge commit `f5880e7` (parents ef04537, 8bf2333) touches exactly h3's Proof.lean.
- 20:45:43 UTC bot commit `b3779de gate: #36 pass` (~10 min after merge). graph.json: h1–h3 proved, h4 ready, root
  blocked. Attestation 000036: pass, kernel, pr-approval by thisisanameforsure, merge_commit f5880e7; submitter null,
  model_and_tooling undeclared (third time). No `ledger/`. Started `round.sh 37`: #37 behind_by 11 → head `cb890ba`,
  approved 20:46:21. Site at b3779de by 20:46:45 (≤62 s): h3 page shows proof commit f5880e7, attestation 000036.
  Api frontier at `rendered_from f5880e7` by 20:46:56 (≤73 s), euclid entries: h4 only.
- #37 round: both runs on cb890ba success, no re-run, `mergeable_state: clean`. Merged #37 at 20:57:19 UTC, merge
  commit `7f81053` (parents b3779de, cb890ba) touches exactly h4's Proof.lean. All four holes merged.
  Expectation from `graph.derive_statuses` (graph.py:278–296): root has no Proof.lean and every dep proved → derives
  `ready`, enters the frontier with `ready_since` set; still `claimable: false` (target listed, mechanical-only, no posting). Waiting for `gate: #37`; then the root should unblock.
  Round helper for #36/#37: `round.sh` (update → approve → wait → re-run failures once → clean; merge is manual).
- CONFIRMED (root B refusal): `gate/opn_gate/steps/stage.py:84` raises `dep-unproved` for every node in the declared
  META `deps` closure lacking a merged Proof.lean, independent of what the submitted proof imports or uses. Once a
  skeleton has merged, a direct proof of the parent is refused until every hole is proved — a "second way" cannot
  land first, and a direct proof can never route around a hard hole. Protocol question (D-3 blocked, D-29), not a typo.
- Tester status (its writes.log, ~20:15): no writes since W15; polling PR state from GitHub's anonymous API and tracking
  the 60/h budget ("24 left, resets 20:35Z") — the service offers no way to watch a submission's review/merge state, so
  a contributor burns GitHub's anon rate limit to learn it. Has `root_run.py` staged for the root proofs.
  Confirmed later: its writes.log says "GitHub anon API budget exhausted until 20:35:08Z" at 20:23:37 — it was blind
  to its own PRs for ~12 min; it fell back to the service's info `rendered_from`. Still no writes after W15 by 20:35.
- Pre-review of the tester's staged root proofs (its scratch `lean/`):
  - **A, assembly**: the merged skeleton's assembly with each `sorry` replaced by the hole theorem
    (`infinitude_of_primes__h1..h4`), then Euclid on n!+1 via `prime_divisor`, `dvd_fact`, `dvd_consecutive`.
    This is "finalizing" the proof through the graph's own decomposition.
  - **B, direct**: self-contained; `Nat.minFac (n! + 1)` is prime (`Nat.minFac_prime`), bridged `Nat.Prime → Opn.IsPrime`,
    contradiction via `Nat.dvd_factorial` + `Nat.dvd_add_right`. Uses no hole node. Genuinely a different proof
    (Mathlib's minFac rather than the skeleton's strong-induction prime divisor).
  - Both are the full `Statement.lean` header with the `sorry` replaced. Open question for B: A and B are both
    `nodes/infinitude-of-primes/Proof.lean`; once A merges the node is `proved` — can a second proof land at all?
  - Answer in code: `modes._locate_change` (modes.py:633–643) refuses a modified Proof.lean with
    `proof-replaces-merged`, whose message names the route: a later proof goes to
    `nodes/<id>/attempts/<ts>-<pseudonym><ALTERNATE_SUFFIX>` (D-25, cites "D-3 v3.13"). So B has a designated path,
    but only a refusal message tells you so. A *new* Proof.lean on a node that has one is status "M", same refusal.
  - `ALTERNATE_SUFFIX = "-alternate.lean"` (paths.py:47, postmerge.py:231). The public /docs/ page has no occurrence
    of "alternate", "second proof", "another proof" or "later proof" (checked 21:00 UTC).
  - The refusal cites "D-3 v3.13"; `docs/` holds only `architecture_decisions_v_3_12.html` and the site renders v3.12.
    A gate message citing a decisions version that does not exist.
  - `modes.check_alternate` (modes.py:1363–1403): refuses `alternate-unproved` (node has no merged Proof.lean) and
    `alternate-duplicate` (byte-identical to Proof.lean or a recorded alternate); similarity never judged.
    `postmerge.record_alternate` files it as `attempts/<stamp>-<pseudonym>-alternate.lean`, never touching Proof.lean.
    So B's route: wait for A to merge, then submit B at the alternate path.
  - Graph AGENTS.md mentions alternates once (line 526), as "a losing racer's complete proof is recorded as an
    alternate in `attempts/`" — checking whether a deliberate second proof's submission path is documented.
  - CONFIRMED undocumented: AGENTS.md's permitted-paths table (lines 300–301) lists `attempts/<ts>-<you>.yaml`
    (postmortem, anyone) and `attempts/<ts>-<you>-partial.lean` ("the gate"), no `-alternate.lean` row. Line 526 reads
    as something the gate does to a losing racer, not a route a contributor takes. The gate has a full `alternate`
    building mode (modes.py:66, 76, 667–668; paths.py:165). The site renders nothing named alternate
    (no match in site/opn_site). A second proof that merges would be invisible on the node page.
  - `Classification.needs_review` is False for `alternate` (modes.py:188–191, "D-4 v3.13": step 9 met by the first
    proof; a later proof changes no verdict, status, dependency or credit, F07-Q20). So B needs no approval.
    Contradiction: AGENTS.md:526–527 says the alternate is "credited too (D-25)"; code says no credit and the ledger
    writes nothing anyway. `postmerge.record_alternate` has no caller (the file already lands at its attempts path).
  - Graph gate.yml: the step-9 review step runs only `if needs_review == 'true'` (lines 158, 338); the build and
    post-merge re-derivation run when `needs_gate` (alternate is a BUILDING_MODE, so it gets a signed attestation);
    the ledger step is proposal-only (line 446). Whether any of this applies live depends on the euclid pin
    `0e3bab6` containing alternate mode — checking.
  - **LIVE PIN HAS NO ALTERNATE MODE.** At network `0e3bab6` (euclid's gate-spec pin), modes.py has 0 `"alternate"`
    and paths.py has no `ALTERNATE_SUFFIX`; `git log -S'ALTERNATE_SUFFIX = '` finds no commit reachable from HEAD.
    Everything read above about alternates (and the "v3.13" citations) is newer, unpinned code in the network
    repo's working tree. What B hits live is whatever the pinned classifier does — checking.
  - Source: a PARALLEL SESSION committed network `cbaff8a` "F07: a theorem keeps every proof — decisions v3.13
    (D-3, D-4, D-25) and the alternate spec" on main during this test, and has `gate/opn_gate/modes.py` and
    `paths.py` staged. Not mine; do not touch those files.
  - Live pin `0e3bab6` paths.py:75–76: `Proof.lean` may be A **or M**; paths.py:161: any `.lean` under attempts/ is a
    `partial`. So live: B submitted over Proof.lean passes the path rule and, if merged, OVERWRITES proof A —
    the defect v3.13 fixes. B at `attempts/…-alternate.lean` would classify as a partial on a proved node.
  - My rule as merger for the rest of this test: never merge a PR that modifies a merged Proof.lean.
- The `node-not-in-frontier` 404 in the tester's log came from `claims.find_entry` (a claim on the blocked root), not
  from precheck. Blocked nodes are absent from the frontier, so the service says "not in the frontier" rather than
  "blocked on deps h1–h4".
- My own watcher bug: zsh does not word-split `$nums`, so the first loop never fired on #35–#37.

## After the stop (2026-09-14)
- #37's post-merge job landed as `0801922 gate: #37 pass`. On graph main, h1–h4 are `proved` and the root
  `infinitude-of-primes` derives `ready` (cause null); the api frontier (`rendered_from 7f81053`) lists the
  root with `ready_since 2026-09-13T20:57:18Z` and `claimable: false` (target `listed`). No proof of the root
  has been submitted.
- Ruleset `22508489` before any F07-T8 change: required checks exactly
  `[{"context": "gate (steps 1, 2 and 4-8 in the sandbox)", "integration_id": 15368}]`, strict up-to-date.
- 2026-09-14T04:42:40Z — set `OPN_API_CLAIMS_URL=https://api.openproofnetwork.org/claims.json` on the graph repo
  (Mike's decision 3). Checked first: the pinned network `0e3bab6` cli defines `--claims-url` (cli.py:251); graph
  gate.yml reads `vars.OPN_API_CLAIMS_URL` behind `${OPN_API_CLAIMS_URL:+--claims-url ...}` (lines 427, 433);
  `GET /claims.json` answers 200 `claims/v1`. Effect is visible from the next post-merge bot commit's products.
