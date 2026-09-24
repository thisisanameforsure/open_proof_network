# 2026-09-24 — six agents on the three calibration targets, and what they found

Mike: "send out … agents to work on the 3 testing problems for the next hour. They should aim to
prove the problems but also make note of any bugs they encounter" (twelve asked for, six sent on
his revision). Two agents per target (`erdos-1050`, `erdos-69`, `erdos-402`), one MCP first and one
plain HTTP, each a fresh cloud session given only its problem page URL, 12:24–13:25Z. None read the
network's source. Their logs are in `engineering/evidence/testers-2026-09-24/`; no token or nonce
is in any of them.

A first round of six, started at 11:48Z, never reached the network: the cloud environment's policy
refused `openproofnetwork.org`, `api.openproofnetwork.org` and `axle.axiommath.ai` (proxy 403), and
each agent logged that and stopped, as instructed. A running container keeps the policy it started
with, so after the owner changed the environment to Custom plus the three hosts, a one-command probe
session confirmed the change before the six were sent again. Those six blocked logs are not kept.

## What landed on the graph

Thirty-one graph pull requests (#174–#204). Nine had merged when this note was written (#174–#182,
the last at 13:30Z), every one by the merge actor with no human; the rest are in its queue, which
drains at about one pull request every seven to eight minutes (below, finding 1).

- **erdos-402.** Proved and merged: `variant-3377fd96` (some x has minFac x ≥ |A|, #177) and
  `variant-6bd06d63` (|A| = 3, #178); #181, a second proof of 3377fd96, merged as its alternate
  (F07-T36 working as built). Queued and green: proofs of the large-prime case (#182 merged; #183 is
  its racer), |A| = 4 (#191) and |A| = 5 (#192); new partial variants for |A| = 6 (#188 and #189,
  one per agent), 7 (#190, #198) and 8 (#197); two annexes (#193, #200). Proofs for 6, 7 and 8
  exist and are fast-checked against the proposed statements, waiting on the nodes to merge; the
  generator is in the HTTP agent's log. #195 carries a wrong witness and will fail step 7 (finding 2).
  Nothing on `erdos-402--h3-v2`, which is Balasubramanian–Soundararajan in full.
- **erdos-69.** Three circularity claims merged (#176, #179, #180): `--h4`, `--h2-v2--h1-v2` and
  `--h2-v2` each follow from the node above them, with exhibits the gate elaborated, so every open
  node under the root is the root restated. A postmortem (#175) merged; an approach record (#184) and
  the root's closing assembly as an annex (#186) are queued; #187 and #194 duplicate the merged
  claims (finding 4). No progress on the mathematics of Erdős 69 itself.
- **erdos-1050.** Annex #174 merged in 92 s. Both agents skeletonised `erdos-1050--h1-v2` in
  parallel: #196 (one hole, with Borwein's Lemmas 4 and 5 and the transfer proved inside the
  assembly, ported from Trevor Morris's Apache-2.0 lean-gallery with credit) and #199 (two holes,
  Padé route). Also annexes #185, #201, #204 and a speculative crux (#203; #202 its red first try).
  The remaining hole in #196 is Borwein's integrality lemma; the recipe for its witness is in the
  MCP agent's log. Two partials on one node is a collision the post-merge job has not met before
  (finding 5).

## Verified findings, in priority order

C = confirmed by me (how), P = plausible, not reproduced, X = the agent's reading was wrong.

1. **The queue is serial and slow under load** (all six; C from the graph's history). Nine merges
   12:31–13:30Z, 7–8 min each, whatever the kind: every pull request is brought up to date (the
   ruleset is strict), its gate re-runs (3–6 min on a Mathlib target), it merges, and nothing moves
   until its post-merge job commits (~3 min, F07-T33, deliberately). A 15-second append costs the
   same round as a Mathlib proof. Thirty-one pull requests in thirty minutes is a four-hour queue;
   none of four agents' proposals could be proved in the hour, since a precheck against a pending
   node is `409 node-pending`. The `waiting_on` flapping between `merge` and `branch-update` that
   four agents reported is this cycle, read at different moments. Neither lever is a bug fix; both
   are the owner's (below).
2. **`witness_preflight` says `matched` for a witness that does not elaborate** (402-MCP, #195; C
   by reading `api/opn_api/checks.py` `preflight_witness`: it returns `matched` when the metaprogram's
   `matches` is true and never reads the checker's `okay`). A `decide` that proves the statement false
   still has the right type. The gate caught it at step 7, one queue slot later. Fix: `matched` only
   when `okay` is true, else `inconclusive` (or refuse, if the owner wants the courtesy to bite).
3. **`GET /submissions.json` (MCP `list_submissions`) takes up to 29 s cold** (1050-MCP twice, 69-MCP;
   C live: 28.5 s, then 0.7 s and 0.5 s inside the cache window). `pending.snapshot` reconciles each
   open record against the host one after another, several API calls each, so the cost grows with the
   queue: 22 open records made it 28 s. Fix: one listing call for all open pull requests, or the
   reconciles in parallel.
4. **Duplicates the service could see and did not mention** (all six).
   - The same pseudonym can hold two active claims on one node (69-HTTP, 402-MCP; C by reading
     `claims.post_claims`: the only check is the per-identity cap).
   - `claim_node` / `POST /claims` never says another pseudonym holds the node, and the frontier's
     claims carry no creation time, so two agents claimed the same five variants nine seconds apart
     (402; C, the claim receipt is the claim alone).
   - A defect claim of the same class on a node already claimed circular, merged or open, is accepted
     (#187, #194; C by reading `duplicates.check_append`: only byte-identical text is refused). By
     Mike's rule (many proofs, never a copy) these are not copies, so whether to refuse, warn or allow
     is his call; a warning in the receipt is the cheap half.
   - Two variants per case on 402 (|A| = 6 and 7 proposed by both agents, different Lean texts).
5. **Two partials on one node** (#196, #199 on `erdos-1050--h1-v2`; P). Whichever merges second
   decomposes a node that is already decomposed. Nothing in the record says what the post-merge job
   does then; check before #199 reaches the head of the queue.
6. **A circular node reads `status: ready`** (69-MCP; C in `graph.json` at main: all three carry
   `status: ready, cause: circular`). The site says circular and the frontier drops them, but an agent
   reading `get_node` or `graph.json` as the guide teaches sees a ready node. Either the guide says to
   read `cause`, or circular becomes a status (a schema bump).
7. **Small ones** (C unless marked): `GET /submissions/<id>` drops `runs[].jobs` once a pull request
   closes, so a client crashes on a merged one (`githost.py` emits the key only when fetched); the MCP
   `get_schema` description names `defect-claim/v1`, which lacks the circularity class the tool
   writes (v3); a tactic-level `set_option maxHeartbeats` does not lift the 200000 cap and a proof may
   not add a command-level one, so the guide should say long case splits must be made cheaper (P for
   the gate's own limit); the HTTP path cannot find the tutorial node without the raw repository
   (`/frontier.json` omits it because it is proved); a proposal's `GET /submissions/<id>` does not
   show the proposed statement; the site key has no "circular"; AXLE's linter warns on the `__`
   in names the gate generates.
8. **Not the network's** (X): every connection reset and empty poll (four agents) came from the
   sessions' egress proxy, which said so itself (`ws_closed_mid_exchange`); the service's
   `/frontier.json` `rendered_from` naming a newer commit than the committed file's is the F05-T13
   overlay working (69-HTTP retracted it); `annex-pending` on precheck is F06-T8 as designed.

## Wishes, consolidated

A queue position and "merge attempted, lost to #N" on `waiting_on` (four agents); withdrawing one's
own pull request (three); a warning when others hold the node (three); precheck against a proposal
whose gate is green (two); the proposed statement on a proposal's submission (two); hazard pre-screen
on `/check`; hole `closed_type`s in the precheck answer; proved `have`s not becoming witness
obligations of later holes (a D-29 question, the owner's, raised again).

## The owner's calls this run raises

- **Queue throughput.** Two levers: let append-only pull requests (postmortems, annexes, claims,
  approach records, which add new files and cannot conflict) merge without the strict up-to-date
  rule or without waiting their turn behind a Mathlib round; or merge a batch of compatible green
  pull requests per round. Either changes the ruleset or F07-T31/T33's discipline.
- **Duplicate defect claims:** refuse, warn or allow (finding 4).
- **The network repo's CI** runs the 46–60 minute Lean tier on every pull request, including a tester
  log that touches one markdown file; twelve such pull requests were opened by the tester sessions'
  automatic draft PRs. A job-level skip for docs-only diffs (not a workflow path filter, which would
  leave a required check unreported, 2026-09-10) would fix it.

## Things worth keeping

- **A cloud session's network policy is fixed at start.** Changing the environment does not reach a
  running container, so "try again" needs a new session, and a one-command probe session is the cheap
  way to learn whether the change took before sending six agents.
- **Each tester session opened its own draft PR on the network repo for its log**, because the
  environment's default is to open one after a push, and each such PR paid the full Lean tier. Next
  time, have testers push to a branch without a PR, or collect logs through one lead session.
- **Six agents in an hour produced 31 graph pull requests.** The queue, not the gate or the checker,
  is now what an agent spends its hour on; every agent praised `/check` (1–10 s) and the tutorial
  token (under 3 min).
