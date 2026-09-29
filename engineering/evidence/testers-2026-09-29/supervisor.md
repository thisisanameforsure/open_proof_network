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
  stop but pushed only at the half-hour check-ins; a concurrency group on the CI workflow, so that
  a newer push on the same pull request cancels the older run, is the fix I would recommend but
  it is a change to the owner's workflow and is left to the owner (the 27 already queued drain
  as they finish). This is the 2026-09-24 note's "the network repo's CI runs
  the Lean tier on every pull request, including a tester log" made concrete: it can starve the
  graph's own gate.
- 20:46Z check-in #3. The queue moves again now that the network's CI runs are draining: #231
  merged 20:27:24Z (its gate had waited for a runner since ~19:55Z), #232 at 20:45:18Z; 46 open
  (#233 oldest), so roughly seven hours of queue at one merge per nine minutes. 136 bug headings.
  Five agents have finished their wave early with the work handed off (1050-B, 1050-E, 69-C, 69-D,
  402-D); 402-D withdrew #249 (sets of 14) because its #260 (every set of at most 24) implies it.
  Findings worth the owner's eye already: 69-C's B3 (a circularity claim only has to prove
  ancestor → hole, so any provable hole, and any hole assuming the ancestor, can be marked
  circular); the licence default on annexes (D-23 says unlicensed prose is not accepted; the
  service records CC-BY-4.0 when none is sent); the target record's attribution of erdos-69 to
  Erdős 1948 (Tao–Teräväinen 2025 per the agents' reading; not verified from here, arXiv is
  blocked in this container); `/check` answering okay for `admit` and an unfinished `apply?`.
- 21:19Z check-in #4. Merges every 6–8 min since 20:45Z (#233 20:54, #234 21:01, #235 21:08, #236
  21:14); 44 open, oldest #238. 137 bug headings. Fifteen of eighteen agents have handed off; 402-B,
  402-C and 69-A run to 21:40Z. The mathematics of the wave, as the agents report it and pending
  merges: on erdos-1050, spec-440db0f9 merged (#234), h3 (`hden`) has a complete proof green in
  the queue (#292, 1050-A) and a second withdrawn as its duplicate (1050-C), h4 (`hrem`) has a
  complete fast-checked proof (1050-A and 1050-D independently) waiting only on the witness #294,
  and h2 carries a one-hole partial (#290); with h3 and h4 the second merged skeleton closes
  h1-v2, and the root closes through it. On erdos-402, cards 11 and 12 are nodes with green proofs
  (#298, #299), cards 9, 10, 16, 18 have green proofs, the reduction lemma and structure lemma are
  merged nodes, and h3-v2 carries a skeleton with the prime and prime+1 cases proved (#289). On
  erdos-69 the target is what it was: the identity was already proved, the remaining hole is the
  theorem, and the agents' contributions are variants, ingredient lemmas, an annex on the
  literature route and a correction to the target's attribution.
  Wave 2 will be six agents, one per pseudonym, each continuing all of its pseudonym's Handoff
  sections; the queue is the only thing they wait on.
- 21:22Z wave 2 launched early for five of six pseudonyms (their wave-1 agents had all handed
  off); 402-P1 follows at 21:46Z when 402-B and 402-C time out. 69-A's final report adds that
  variant-09e95e7a (Σ_p 2^-p irrational) was already proved on the record, which 69-B had found
  too and proposed three stronger variants instead; and that a "if the ω-series is rational then …"
  lemma can never pass step 7 (its hypothesis is false, so it has no witness) and must be stated
  for a general f, which is worth a guide sentence.
- 21:26Z 1050-P2 reports that its `DELETE /submissions/<id>` for #274 was refused by this session's
  permission classifier ("External System Writes") before it reached the service; it did not
  work around it and neither will I on its behalf. #274 stays open (harmless: one queue slot).
  Wave-1 agents' withdrawals went through, so the classifier's verdict is not consistent; if it
  also refuses a wave-2 agent's precheck or submission the run's landings stop there, and that
  is for Mike, not for a workaround.
- 21:45Z check-in #5. Merges every 4–12 min (#238 21:21, #239 21:29, #240 21:33, #243 21:40);
  42 open, oldest #244 (402-B's card-10 proof). 147 bug headings. All six wave-2 agents are
  writing; the proofs of #238 and #239 (69-A's and 69-E's nodes, now merged) are the first
  wave-2 submissions to expect. Pushed.
- 22:18Z check-in #6. Merges: #244 (402-B's card-10 proof, the run's first proof of a pre-existing
  open node to merge) 21:51, #246 (card 13 proposal) 22:00, #248 (annex) 22:09; 41 open, oldest
  #251, newest #304; 151 bug headings. Wave 2's first landing: 69-P2 prechecked and submitted
  69-E's proof of spec-2e765953 as #302 within twenty minutes of the node merging, so the
  hand-off through the log files works. 1050-P1's line (#292 hden, #294 h4 witness) is about
  eighteen merges back, roughly 00:30Z. Pushed.
