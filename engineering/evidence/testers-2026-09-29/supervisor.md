# Supervisor notes — 2026-09-29 tester run

- 19:00Z start. Tokens t0929-1..6 minted 19:02–19:08Z (t0929-5 needed a second try: a TLS
  handshake reset from the container's egress proxy during a poll; the first precheck's nonce was
  never spent). Six anonymous prechecks and six token starts used of the day's 20 and 10.
- 19:05Z wave 1 launched: 15 agents, then 402-A/B/C at 19:09Z once t0929-5 existed (the times in this file are read from `date -u`, not guessed; the first draft of this line guessed and was wrong by seven minutes).
- 19:09Z 69-C reports my assignment was built on a misread: erdos-69--h1-v2 (proved) *is* the
  prime-sum identity, and h2-v2 is the irrationality given it (circular by a merged claim). So
  69-A's speculative node would re-prove a proved statement and 69-C's skeleton would duplicate
  the merged 2026-09-17 one. 69-C redirected to an annex on h2-v2 plus a skeleton of it with the
  literature's ingredients as holes; 69-A redirected to prove one such ingredient. Lesson for the
  bug list: the problem page shows h1-v2 as "proved" and h2-v2 as "circular" but not what either
  says, so a planner reading the page (me) assigned work that was already done.
- 19:11Z PR #24's fast tier went red: ruff lints the whole tree and the agents keep the Python behind
  their numeric checks beside their logs (`402-G/colour.py`, 49 findings). Fixed by excluding
  `engineering/evidence` from ruff in `pyproject.toml`, the same way `docs/` is; `make lint` green
  locally (ac5f9f6).
- 19:15Z 402-F reports complete verify-okay proofs of all four open card variants (9, 10, 16, 18)
  in its evidence directory, unsubmitted, built on its reduction lemma (proposed as
  spec-fa8046e4). 402-A and 402-B have their own proofs of 9 and 10 (B prechecking), so F keeps
  V9/V10 unsent; F prechecks and submits V16 and V18 (`decide +kernel`, a live test of the gate's
  replay budget); 402-C and 402-D stand down from 16 and 18 and take cards 13 and 14 (402-G has
  11 and 12). Agents' log timestamps were running ahead of the clock (402-A's log said 19:20Z at
  19:15Z); every agent is being told to stamp from `date -u`.
- Queue at 19:15Z: 13 open pull requests from this run (5 speculative, 3 variants, 3 annexes, 1
  proof, 1 revision request), all `waiting_on: null`; nothing merged yet.
- 19:36Z **The service's GitHub App installation hit GitHub's hourly API rate limit.** Reported by
  69-C (POST /precheck → 502 dispatch-failed "API rate limit exceeded for installation ID
  160370091" at 19:35:55Z); confirmed by my own read at 19:38:04Z: `GET /submissions/<id>` answered
  with `pull_request: null` and `pull_request_error` quoting GitHub's 403 on
  `GET /repos/…/pulls/276`, while `/health` said ok and `/submissions.json` (43 open) carried no
  error field at all. Cause on our side: eighteen agents polling `/submissions/<id>` (each read
  goes to the host) and `/submissions.json` (which reconciles every open record against the host,
  finding 3 of 2026-09-24) on top of the merge actor's and the precheck dispatcher's own calls.
  Broadcast to all eighteen: submissions by id at most every 5 min, the listing every 10 min,
  prechecks every 60 s, no tight loops, retry failed dispatches after 20:00Z. This is the run's
  first major finding: unauthenticated reads spend the service's own host budget, and when it is
  gone prechecks cannot dispatch and (to be confirmed) the merge actor cannot act.
- 19:42Z check-in #1. 102 bug headings across the eighteen logs already (69-D 18, 1050-E 14,
  69-E 11, 69-C 8, 402-G 8); the aggregation is for the end of the run, but three clusters are
  already visible: the host rate limit (every agent), the fast check's id named three ways and
  its read-back route undocumented (six agents), and the guide's rules the gate does not enforce
  (annex citation, `clear`ed hypotheses inherited by later holes). Queue: 43 open pull requests
  (#230–#276) from six pseudonyms; the graph's `main` (2b94322) is ahead of the products'
  `rendered_from` (f9b33c0), so merges are happening; at ~8 min a round the queue is about six
  hours deep, and most agents now hold finished proofs waiting for their proposals to merge.
  Collisions caught from the Handoff sections: 1050-A had proofs ready for three of 1050-F's
  proposals, and 69-D one for 69-A's #271; both told to keep them unsent. Two partials on
  `erdos-1050--h1-v2--h3` (#253 five holes, #275 one hole) are left to run: the record already
  carries two merged partials on `erdos-1050--h1-v2`, so the collision is a known-handled case.
  Plan for wave 2 (21:45Z): nine agents, not eighteen — the queue, not proving, is the bottleneck,
  and every pseudonym's next step is "precheck and submit when the node merges", which one agent
  per pair can shepherd while hunting bugs. Halves the usage rate.
- 20:15Z check-in #2. 129 bug headings; 47 open pull requests (#231–#290); the host rate limit has
  reset (a by-id submission read carries no error). **The merge queue has not moved since #230
  merged at 19:45:28Z (bot commit 19:53:14Z)**, read from a shallow clone of the graph, while 47
  green pull requests wait: a 22-minute gap where the run's first hour had a merge every 8 min.
  The rate-limit window (19:36–20:00Z) covered the post-merge dispatch that wakes the actor after
  #230, which is the freeze shape the 2026-09-23 replay found (a dropped wake, then nothing until
  the cron). Cannot be confirmed from here without reading the graph's workflow runs; requesting
  read access to the graph repository for that one purpose.
- 20:17Z **The queue stall is mine.** `GET /submissions/<id>` for #231 says `waiting_on: gate`
  with its gate run `queued`, and the network repository's Actions list shows 27 CI runs from
  this branch in progress or queued (one per push of these logs, each running the hour-long Lean
  tier), which is the account's whole hosted-runner capacity. The graph's gate for #231 has been
  waiting for a runner since the actor updated it. I could not cancel them (the App has no
  `Actions: write`, 403 on every cancel). Two changes: the evidence is now committed at every
  stop but pushed only at the half-hour check-ins, and the CI workflow gets a concurrency group so
  a newer push on the same pull request cancels the older run (it cannot clear the 27 already
  queued, which drain as they finish). This is the 2026-09-24 note's "the network repo's CI runs
  the Lean tier on every pull request, including a tester log" made concrete: it can starve the
  graph's own gate.
