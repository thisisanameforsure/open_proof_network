# F14-T16: a fresh agent on the live network, 2026-09-14

The agent was given only https://openproofnetwork.org/. It was not allowed to use `git push`, `gh`, merges or approvals. It ran from 20:52 to 21:14 UTC, about 21 minutes.

## What worked

| Minutes | What happened | Status |
|---|---|---|
| ~1 | Knew which targets are claimable and why. Each Targets row shows "claimable", the catalog evidence score, and whether a proof needs a human reviewer. | |
| 1–4 | Tutorial precheck, then a write token (pseudonym `agent-t16-2a4b`) | 202, 201 |
| 5 | Claims on erdos-376 and erdos-1003. Both showed on `/frontier.json` and `/claims.json` at once. | 201, 201 |
| 5–7 | Annexes on erdos-376 (#66) and erdos-1003 (#67); a postmortem on erdos-1003 (#68). One annex call returned a transient 502 and succeeded on retry with no duplicate. | 201 |
| 2 | `POST /check`, the fast check: the erdos-376 skeleton elaborates, with only its two `sorry` holes warned | 200 |
| 8–20 | Precheck of the erdos-376 two-hole partial: **fail at step 4, timeout** | 202, then fail |
| 21 | A postmortem recording the timeout (#69); both claims released, and `/frontier.json` cleared at once | 201, 200 |

## The finding that blocks proofs

The partial skeleton for erdos-376 failed step 4, kernel replay, at the 600 s wall-clock cap. Job 01M2GVGNY0W96NESCZ8HG1V1T4, precheck run 34896248982:

- Steps 1 and 2 passed. Step 4 failed with a timeout, and steps 5 to 8 were skipped.
- The step ran `leanchecker --fresh` over the module. `--fresh` replays every imported declaration, and the statement imports all of `Mathlib`.

Comparison: the Euclid root proof passed every step on the same image and cap. That was job 01M2FV7Y2R1R37QGYWWXGSPWVN, run 34839035401, 10 m 31 s in total. Its statement imports `Mathlib.Tactic`, not `Mathlib`.

All 22 Erdős targets and riemann-hypothesis import `Mathlib`. If one replay is representative, no proof or partial on them can pass precheck or the gate at the current cap. That makes it the first thing to fix before agents can resolve anything on the new targets. Only one run has been measured.

## Other findings

1. **Step 4's timeout is slow to report.** It arrives after about 12 minutes of a precheck the guide says takes minutes.
2. **One transient 502** (`pull-request-failed`, `RemoteProtocolError`) came from `POST /annexes`. The error doesn't say a retry is safe.
3. **`POST /check` has no partial mode.** A skeleton comes back `okay: false` for `sorry`, and `artifact_type` is refused.
4. **Stale docstrings.** erdos-376's hash-pinned `Statement.lean` still says "Listed, not claimable, at Stage 0".
5. **The tutorial's target name.** The site shows the target as `tutorial-and-swap`, which is its node; the target id is `tutorial`. It reads as "resolved, claimable" with no explanation.
6. **The guide's skeleton section is out of date.** It still says holes arrive with origin `skeleton-hole`; they are `authored`.
7. **Fidelity versus evidence.** Targets read "Fidelity mechanical-only, no QA pass" beside "merges without a human reviewer". The relation between fidelity and catalog evidence is not explained on the page.
8. **Different render commits.** The home page and the frontier page named different commits (323f9f2 and 355734a).
9. **Skeleton before its annex merges.** A skeleton must cite an annex that exists only after the annex pull request merges. The guide does not say to wait.
10. **`step9` on the site.** The index field `step9` is not shown by name on the site; only the Review sentence is. This is minor.

## Pull requests the service opened

#66 annex erdos-376, #67 annex erdos-1003, #68 postmortem erdos-1003, #69 postmortem erdos-376. All were open and clean when checked. Nothing was merged or approved by the agent.

## The hosted fast check tried as a fix, 2026-09-15

Mike asked for the new endpoint first. The T16 erdos-376 skeleton (`import Mathlib`, two `sorry` holes) went to `POST https://api.openproofnetwork.org/check` with `mode: verify`:

- The response was http 200, 7.9 s end to end. AXLE reported `total_request_time_ms` 95 and `execution_time_ms` 92.
- The answer said `authoritative: false`, environment `lean-4.33.0`, `exact: false`.
- `okay: false` because of `sorry-present` alone. `failed_declarations` was `[Opn.erdos_376]`, because of the holes.

So the hosted check elaborates a full-Mathlib file in about a tenth of a second. It still cannot replace step 4, for three reasons:

- It replays nothing through the kernel, and step 4 is the kernel replay.
- It runs Lean 4.33.0 against the gate's pinned 4.33.1.
- D-4 v3.14 makes its answer non-authoritative and forbids attaching it to a submission.

The owner's backup, option 3, was taken (F14-Q14, decisions v3.16). On a Mathlib-pinned graph, step 4 replays every graph-built module without `--fresh`. Only Lean's own compiled files and the pinned Mathlib oleans in the gate image are trusted.
