# 2026-09-23 — nine agents on three Erdős targets, and what they found

Mike: "send 9 agents to work on the 3 open erdos problems using opus 5.5 for the next 40 minutes …
have them report any bugs that they find. It will be your job to condense and verify their bugs."
Three agents per calibration target (erdos-1050, erdos-69, erdos-402): one MCP first, one plain HTTP
following the guide literally, one mathematics first; each with its own scratch directory and log
(`engineering/evidence/testers-2026-09-23/`), 14:41–15:20Z. None read the network's source.

## What they did

Nothing settled a target: in each the one remaining hole is the published theorem itself (Borwein for
1050, Tao–Teräväinen for 69, Balasubramanian–Soundararajan for 402). They proved erdos-69's h1–h3 (three
agents, different texts), proposed variants of 402 for |A| = 3, 4, 5, a minFac case and a large-prime
case, proved one (#170), and wrote annexes and postmortems showing two skeletons were circular.

## Verified findings, and what was done (Mike's rulings, 2026-09-23)

| # | Finding | Verified | Done |
|---|---|---|---|
| 1 | The merge queue froze 14:53–17:15 and again from 17:51 | C: the actor held on a check the host reported late, a hold ended the run, run status lags jobs by minutes, `mergeable: null` read as no conflict, the concurrency group drops wakes, the cron ran every 3–6 h; its own program run by hand said `merge #148` | F07-T32 (settle, jobs, dispatch after post-merge and after a failed run), live: the frozen queue woke 14 s after the push and drained |
| 2 | #145's proof never attested; variant-d865c9c6 open and claimable for two days | C: five merges (#125, #130, #132, #133, #145) had lost their bot commits since 09-20, a sixth (#157) was lost live; the actor moved main under each post-merge job | F07-T33 (nothing moves main under a job; replay by dispatch; the attesting gate is the merge's own pin), all six replayed, variant-d865c9c6 proved on the site |
| 3 | Duplicates accepted silently | C: #150 = #146 but for comments; #168/#171 one statement; the erdos-69 proofs all different | Mike: many proofs, never a copy. F07-T35 (409 duplicate-submission), #150 and #168 closed with comments and their agents told; F07-T36 (a losing racer becomes an alternate, as D-25 always said), live on #162/#163/#164/#167/#172 |
| 4 | Circular skeletons | P→C for 1050 (the exhibit fast-checks), P for 69 | F07-T34 (no hole may be defeq to any ancestor), F08-T17 (a gate-checked circularity claim), decisions v3.21 |
| 5 | Witness only checkable after a full gate round | C | F13-T16 (`/check` witness mode on a statement's text; pre-flight on proposals), live: #168's own witness mismatched in one call |
| 6 | Guide sentences | C: `waiting_on` nesting, approach-record body, witness-slot header, MCP record type, `/check` mode and positions | F10-T13, F07-T37 (the slot writer), F09-T12 (MCP takes text) |
| — | `waiting_on` missing | X: it is at `pull_request.waiting_on` | a guide sentence |

## Things worth keeping

- **A replay that does not model the host's lag cannot find a stall.** T31's replay ran the actor every
  fifteen seconds and read every status exactly, so every stall of the afternoon was invisible to it. The
  new replay wakes the actor only when the host would, reads statuses as late as the host reports them,
  keeps one pending run, and has no cron; it reproduced both freezes on the first run.
- **"A hold here is always woken" was a claim about an event that had already happened.** Every way a run
  can stop now has a wake after it, and the test enumerates them.
- **An exemption for speed was a hole in the record.** T31 let appends through while a post-merge job ran,
  because their gate takes seconds; each such merge moved main under the job and cost it its record.
- **The trigger must be the fact, not the host's flag.** The racer rule waited for `mergeable_state:
  dirty`; GitHub answered `unknown` for five minutes on #172. A proof PR on a proved node can never merge.
- **My own probe wrote the wrong proof to the record.** Re-running a write-reproduction after the service
  had already converted #172, the probe read "Proof.lean at the head" (by then main's, the winner's) and
  pushed it as #172's alternate; repaired within a minute from the saved original and checked byte for
  byte, and written into the evidence. A probe that writes re-reads immediately before acting, and never
  runs twice.
