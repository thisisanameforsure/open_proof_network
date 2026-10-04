# The audit's fixes: what is built, and the owner's sitting that makes it live

Built 2026-10-04 on local `main`, test first, and **nothing is pushed**. Pushing the network
deploys the api, so every step below is the owner's.

The graph's live pin is network `3a780d6` (graph `b3211a464`, the F18 session's re-pin of
2026-10-04). Everything here becomes live at the *next* re-pin.

## What is on local `main`

- **Truth.**
  - The meaning comparison runs for every artifact (F08-T28).
  - Judging reads a workspace the compile never wrote (F02-T10).
  - Verdicts carry a nonce and the judges run with initializers off (F02-T11).
  - Steps 7 and 8, admission's relation, and counterexample/vacuity types are judged from compiled modules (F02-T12, F08-T34).
  - A partial's hole extraction (F02-T13) and a circularity exhibit (F02-T14) are judged from compiled modules too. Every forged-verdict route the audit found was shown on Lean 4.33.1 and is now refused, pending the lean tier in CI.
  - Fails closed since F02-T13: a hole that needs an instance or notation declared in a dependency's proof or in the assembly is refused as `hole-not-roundtrip`.
  - F02-T12 changed the Python–Lean argument interface, so the image and the gate code must move together at the re-pin.
- **Traceability, graph side.** On graph branch `audit-b-workflows`, 5 commits rebased on
  `b3211a464`:
  - every merge counts as recorded only if a gate commit names it (F07-T58);
  - a re-pin re-renders the products (F07-T60);
  - the pin step fails closed and reads the pin from the base (F07-T61);
  - the merge actor reads every page and bounds a gate that never started (F07-T62);
  - the submitter recorded is the one the gate saw (F07-T63).
- **Traceability, network side.**
  - The credit sweep (F07-T59).
  - Withdrawal and racer comments (F07-T64).
  - `reproduce` refuses an unpinned checkout (F07-T65).
- **Reversibility.**
  - Withdrawal records (F08-T31).
  - An exit from `disputed` (F08-T32).
  - Credit corrections (F07-T66).
  - Withdrawal parity in the context bundle (F08-T33).
  - Decisions v3.27 §1–§3, applied.
- **Hard to tamper with.**
  - The real source address keys the rate limits (F05-T19).
  - Pre-flights fail closed on a spent budget (F13-T28).
  - A precheck opens one pull request (F06-T11).
  - Open-PR caps of 10 and 150 (F07-T67).
  - Token revoke CLI (F05-T21).
  - Budget-held anonymous reads (F07-T68).
  - Scoped installation tokens (F06-T12).
  - Claims cache (F05-T20).
  - Stack limits, alarms and retention (F05-T22).
  - Cache-path headers (F04-T28).
  - Actions pinned by SHA (F04-T29).
- **State and information.**
  - Closed roots are not claimable (F03-T14).
  - `frontier/v4` with `needs` (F03-T16) and `info/v2` (F05-T25).
  - Error catalog and `/errors.json` (F13-T29, F05-T23).
  - `llms.txt` and `robots.txt` (F05-T24, F04-T30).
  - MCP instructions and three reads (F09-T15–T17).
  - Per-lane queue position (F07-T69).
  - `/submissions/mine` (F07-T70).
  - Check verdicts (F13-T30).
  - Witness-pending refusals (F06-T13).
  - The guide (F07-T71, T72).

`make verify` on `main` (0e68d2e): 3937 passed, 1 skipped (case-folding filesystem), 1 failed. The
failure is `test_walkthrough::test_graph_copy_is_identical`: the network guide is now ahead of the
graph's copy, and the re-pin's guide copy fixes it.

## The sitting, in order

1. **Probe before pushing.** The api deploy now mints scoped installation tokens (F06-T12). If the
   App installation lacks a permission, that mint fails only live.
   - Run the inert probes P1–P9 and N1 from `engineering/evidence/F06/task-12-audit-2026-10-04.txt`.
   - Run the comment probe from `engineering/evidence/F07/task-64-audit-2026-10-04.txt`: a 404 on
     PR 999999 means the App may comment.
   - Keep the output as evidence.
2. **Push the network to `main`.** This deploys the api.
   - Wait for CI. The **lean and docker tiers are the first real run** of F08-T28, F02-T10 and F02-T11
     (`test_finding_meaning_every_proof`, `test_uses_defs_lean`'s Q36 case,
     `test_finding_trusted_workspace_lean`, `test_finding_verdict_channel_lean`).
   - Also first exercised here: the docker stdin plumbing for the nonce, and the new `opn-axioms`
     binary in the image.
   - Read every red before believing it (Log 2026-09-10: one dead daemon looks like eight failures).
3. **Set the token cutover.** Before the api deploy, set `OPN_API_TOKEN_CUTOVER` to the deploy day (F05-T27): existing tokens get a full 90 days from it. Check the live identities against the reserved names with the scan in `engineering/evidence/F05/task-26-audit-2026-10-04.txt`.
4. **Apply the stacks.** Use change sets with `UsePreviousValue`, read before execute:
   - the api stack (F05-T22; `api/infra/README.md`, with `AlarmEmail` set; then mint one token and
     check `IdentitiesMinted` counts it, since the JSON-logging call is inferred, not observed);
   - the site stack (F04-T28; then `check_deploy`).
5. **Graph workflows.** Open graph branch `audit-b-workflows` as a pull request.
   - After F07-T61, only a curator listed on the base may open a non-target pull request, so it must
     be opened by `thisisanameforsure`.
   - Once it merges, take `audit-b-workflows` out of `REFS` in
     `gate/tests/test_finding_merge_actor_workflow.py`.
6. **Re-pin** to the pushed network head, following `engineering/evidence/F00/repin-3a780d6.txt` or
   the latest equivalent:
   1. Tag, publish the images, run `pin_image.py` over every target in a detached worktree, and read
      the devcontainer diff.
   2. Seed the new schemas: `frontier/v4`, `info/v2`, `withdrawal/v1`, `credit-correction/v1`, `graph/v5`, `context/v3`. Every `graph.json` and `CONTEXT.json` changes on the first render.
   3. Copy `gate/agents/AGENTS.md` to the graph.
   4. Commit, then `pregate.sh` with the whole output redirected to a file.
   5. Push with no gate run in flight.
   6. Dispatch `render.yml` (F07-T60, live after step 4) and check that `rendered_from` equals the
      head.
7. **Live checks.**
   - `/frontier.json` is v4.
   - `/errors.json` and `/llms.txt` answer.
   - From outside, a spoofed `X-Forwarded-For` still reaches 429.
   - `gate/tools/uncredited.py --graph <graph>` lists only the acknowledged merges.
   - `tokens.py revoke` works against a throwaway pseudonym.

## Acts on the record (the owner's, after the re-pin)

- Credit corrections for PRs #68, #69 and #71 (F07-T66; F07 Q76 says how).
- Withdraw the six circularity claims filed under the pre-v3.23 direction (F08-T31, F08-Q33).
- For merges #2, #8, #72 and #73: acknowledge each for good (write its reason in
  `uncredited.ACKNOWLEDGED`) or replay it.

## Built on 2026-10-04 from the owner's five decisions (decisions v3.28)

- Defect claims shown in `graph/v5` and `CONTEXT.json`, and on the site; a curator accepts a dispute with `curator status <node> disputed --reference defects/<file>` (F08-T35, T36, T38).
- A refuted or ill-posed root resolves its target, and the site says "disproved" or "shown ill-posed" (F03-T17, F04-T31, F04-T32).
- Proposed statements hold declarations only (F08-T37), and the exhibit pre-flight matches the gate (F13-T31).
- Reserved pseudonyms (F05-T26) and 90-day renewable tokens (F05-T27).
- The four old merges acknowledged with reasons (F07-T73).
- The api redeploys on any gate module it imports (F05-T28).

## Still open for the owner

- A tutorial identity whose token lapses cannot be re-proved (F05-Q27): it keeps its credit but cannot write again. Options are in the session's report.
- Whether the Problems page gets a "Disproved" filter (F04-T31 left it out).
- `formalizations/<name>/Statement.lean` (F14-R7) is not covered by the declarations-only rule.
- Step 9's reviewer rule, left as is by ruling. It guards against accident, not against a second account.
