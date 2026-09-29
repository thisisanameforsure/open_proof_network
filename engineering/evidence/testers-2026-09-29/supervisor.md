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
