# Bugs found by the 2026-09-29 tester run, aggregated and prioritised

Thirty agent logs in this directory carry 176 `### B` headings; this is their consolidation,
deduplicated across agents, with the supervisor's own two findings added. C = confirmed by more
than one agent or by the supervisor's own read; P = one agent, plausible, not reproduced by
another. The agent and heading in brackets is where the exact request and response are.

## Priority 1 — a blocker or a systemic fault (fix before the next agent run)

1. **Unauthenticated reads spend the service's GitHub App budget, and when it is gone nothing
   works and nothing goes red.** C (every agent; supervisor's own read 19:38:04Z). `GET
   /submissions/<id>` reads the host per call and `GET /submissions.json` reconciles every open
   record against the host, so eighteen pollers exhausted GitHub's hourly limit for installation
   160370091 at 19:35Z: `POST /precheck` → `502 dispatch-failed`, every write that opens or
   closes a pull request → `502 pull-request-failed` with GitHub's raw text and no `Retry-After`,
   `/health` still `ok: true`, and the by-id route served a stale `pull_request` block (with a
   live-looking `waiting_on`) beside a `pull_request_error`. [1050-A B5, 1050-C B5, 402-E B3,
   69-C B7, 69-E B10, 402-A B3/B4, 69-B B2/B3, 69-E B11 and others]. Fixes the agents converge
   on: cache the host state with a visible `read_at`/staleness marker, one listing call for the
   queue, a `Retry-After`, and `/health` reporting the remaining host budget.
2. **The network repository's CI starves the graph's own gate and the prechecks.** C (supervisor,
   20:16Z; 69-C B9, 402-B B8, 402-G B10, 1050-F B7). Every push to a network branch runs the
   hour-long Lean tier; 27 runs from this PR's pushes held the account's whole hosted-runner
   pool, the queue head's gate sat `queued` for 16–24 minutes, precheck jobs likewise, and no
   merge happened for 42 minutes. `waiting_on` read only `gate`. A concurrency group with
   cancel-in-progress on `ci.yml`, or a docs-only skip at job level, is the owner's fix.
3. **The merge queue is serial and slower than a session.** C (all agents). One merge per 6–10
   minutes whatever the kind; 47 open at the peak; a proposal-then-proof round trip took 75–95
   minutes for the first two and up to three hours later; every dependent chain costs k full
   passes. A queue position is nowhere; `waiting_on` flips between `merge` and `branch-update`
   every minute deep in the queue. Also seen: after #305 merged at 04:04Z nothing merged for
   35 minutes with fifteen green pull requests open and the head reading `waiting_on: merge`,
   `mergeable_state: unknown` (the 2026-09-23 freeze shape; not root-caused from here). [69-B B1,
   402-D B2, 402-E B4, 1050-P1 W1 and every Handoff]
4. **The hole extractor ignores `clear`, so a later hole inherits an earlier one it does not
   use.** C (1050-C B1, 1050-D B1, 1050-E B4; live on erdos-1050--h1-v2--h4, whose witness had
   to carry all of h3's 845-line proof, and #294 did exactly that). The same proof then passes
   the serial queue twice. Revision request #229 (merged) asks a curator to drop the hypothesis;
   nothing shows a merged, un-acted-on revision request anywhere (1050-D B4, C). Hazard: acting on
   #229 before #294 merges would have superseded h4 under its own witness.
5. **A circularity claim only has to prove ancestor → hole, so any provable hole, and any hole
   whose hypothesis is false, can be marked circular.** P (69-C B3; two sorry-free exhibits
   fast-checked, not filed). A genuinely easier hole can be taken off the frontier by a merged
   claim; the rule cannot tell a cycle from an honest case split (402-E W1).

## Priority 2 — major: the record, the licence rule, the hazard checkers

6. **An annex with no licence is accepted and silently recorded CC-BY-4.0** (HTTP and MCP). C
   (1050-E B5, 69-D B5). D-23 says unlicensed prose is not accepted.
7. **The hazard checkers miss natural-number division.** C (69-A B1, 1050-F B2). `int-trunc`
   flags ℤ division only; `n / 2` and a tsum written without a `: ℝ` ascription become truncating
   ℕ arithmetic and pass step 6 silently, the very trap the gate-written holes fell into on
   2026-09-17. Also: an undeclared identifier in a statement becomes a hidden universal binder
   (`autoImplicit`) and hazards mode says nothing (69-D B30, 69-P2 B2, C).
8. **The ledger and the Contributors page say tooling "undeclared" on every statement line
   (39 of 39) although each node's META.yaml records the proposer's `provenance.model`;
   postmortem lines likewise.** C (402-A B1, 402-B B5, 69-D B21, 69-W3-1 B1, 402-P1). A D-23
   disclosure that never reaches the ledger.
9. **The steward rule is stated as in force on the Home, Problems, About and Docs pages while
   `steward_rule.enforced` is false and every open problem without a steward is claimable.** C
   (402-A B2, 69-D B13, 1050-W3-1 B3, 1050-W4-1 B1, 69-W3-1 B2, 402-W3-2 B3). Same for the
   non-author statement check on the About page.
10. **The target record misattributes erdos-69** to Erdős 1948 (the divisor-function paper) and
    grades it "medium"; the ω result is Tao–Teräväinen, arXiv:2512.01739 (Dec 2025), a 4,700-line
    external Lean proof exists (plby/lean-proofs, no licence file). P→C (69-C B2, 69-D B10; not
    verifiable from this container, arXiv is blocked). erdos-1050's status record still says a
    proof waits for a reviewer (1050-E B11).
11. **The guide says the gate enforces the `-- annex:` citation on a skeleton; it does not.** C
    (1050-B B1, 69-C B10, 402-E B6, three prechecks and one merged skeleton #289 without one).
    Conversely a citation of an unmerged annex is `409 annex-pending`, so skeleton work waits on
    the queue twice, and an unknown hash is answered `annex-pending` naming somebody else's pull
    request instead of `annex-unknown` (69-C B4, 69-D B26, C).
12. **`/check` says `okay: true` for proofs that are not proofs**: `admit`, an unfinished
    `apply?` (69-D B23, 69-P2 B1, C), a header the gate refuses at step 2 (`set_option … in`, an
    extra `open`; 69-A B5, 69-D B29), an alpha-renamed binder in the theorem signature (69-P1 B1),
    and an import of a node that does not exist when no `node_id` is given (1050-A B1).
13. **A proposal cannot be prechecked, verified with `node_id`, or claimed until it has merged
    and rendered** (`409 node-pending`, then `products-pending` with retry-after 240 even 23
    minutes after rendering when the `target_id` is wrong; 69-P2 B7). With the queue this is the
    whole session (402-D B2, 1050-F B1, 69-B W3). The service already serves the proposed
    statement as `proposed_statement`.
14. **A second proof of an already-proved node prechecks clean at `Proof.lean`, spends four
    minutes of sandbox, and can never be submitted** (`400 proof-replaces-merged`); the guide's
    path table, the MCP description and the site's Docs table give three different stories about
    where an alternate goes. C (402-P1 B1, 402-G B2/B5, 69-D B31/B4).
15. **`GET /submissions/<id>` after a pull request closes** loses `runs[].jobs`, the gate
    verdict and the refusal reason (69-D B3, 402-B, C); a withdrawal twice answers 200 and moves
    `closed` (1050-E B6).
16. **The witness rule blocks a node whose witness is an open sibling's full proof**, and the
    node page and frontier say "blocked by nothing else" (1050-D B2, C); `409 node-blocked` does
    not name the witness pull request already open for the node (1050-A W5, 1050-W4-1 W2).
17. **No MCP tool can read a node's `defects/` or `revisions/`** although the guide says
    `get_node` returns the raw files; agents cloned the graph to read the exhibits (69-E B1, C).
    `get_node` also reads through the contents API and reports `graph-unreachable` when the
    quota is out (69-D B19).

## Priority 3 — minor: wrong or misleading answers that did not stop anyone

18. `dropped_warnings` misses the `__` naming-linter warning on revised holes (the `-v2` nodes
    keep the old theorem name) and on every hole theorem pulled in from the Context (1050-E B2,
    1050-P2 B4, 69-C B5, 69-E B4, 402-E B1; 402-W4-2 saw it fixed for the node-named theorem).
19. `get_node`'s `closing.through_holes` is `true` on every node, holes or not (402-B B1,
    1050-W3-1 B6, 1050-P2 B1, 402-P1); the `closing` block exists over MCP only, in no
    CONTEXT.json (69-D B12, 402-G B6).
20. `list_frontier` answers `[]` with no error for a filter value of the wrong shape (a list for
    a list-valued field) and offers no way to filter for unclaimed nodes (1050-F B4, 1050-W3-1 B4,
    69-W3-1 B4).
21. `replacement: null` on superseded nodes whose replacement META names (402-E B5); a
    declaration-clash refusal names the superseded node, not the one holding the name (69-A B2).
22. A proposal whose witness does not compile is refused as `statement-fails` on both proposal
    routes; the witness route says `witness-fails` correctly (69-P2 B3).
23. A precheck declared `counterexample` on a file that is a proof passes every step and the
    answer never records the declared type (69-W3-1 B5).
24. A hole of an open skeleton answers `404 node-unknown` with a message about a merge that never
    happened, and the same words a typo gets; the window after a gate commit is 25–85 s
    (1050-C B4, 402-W4-2).
25. `GET /frontier.json` can answer from an older commit than the call before it (402-G B9);
    `/check` once answered `503 graph-unreachable` for a node whose Context exists (402-G B1);
    `GET /hosted-checkers.json` names a schema the graph does not publish (402-W3-2 B1).
26. A proof that passes step 4 can fail step 8 as `deps-unreadable` on a heartbeat timeout,
    the wrong code (1050-C B6); a precheck reads `running` for 22 minutes with no step or queue
    position (1050-A B6).
27. Duplicates the service could refuse and does not: an identical approach record (69-D B18),
    a revision request on an already-superseded node (69-D B28), a defect claim of a class
    already merged (2026-09-24 finding 4, still).
28. `/check` passes AXLE's `cached_response` through, revealing whether anyone sent the same text
    before (69-E B8); it needs `target_id` even with a `node_id` and reports it missing as a
    regex mismatch (69-E B9, 402-G B3); the id it returns is `log_id`, the route is
    `GET /checks/{check_id}`, the guide never names the route, and anonymous checks cannot be
    read back (1050-A B3, 402-B B3, 402-D B1, 402-G B4, 69-A B3, 1050-E B3; six agents).
29. `targets/index.json` marks a resolved target unclaimable for `status-resolved`, which the
    guide says is not a reason, while tutorial (also resolved) is claimable (69-D B16, 1050-W4-1
    B3); this will bite erdos-1050 the day its root closes.
30. The site never shows active claims, open pull requests or queue position on a node; the
    "pull requests in flight" link goes to the whole graph's `submissions.json`, a route that
    spends the host budget (69-D B32, 402-E W5, 1050-P2 W1, and every agent's wish list).

## Priority 4 — documentation and site text (each a sentence or a template line)

31. The Docs page renders the guide's single-asterisk emphasis as literal asterisks, twelve to
    fourteen places (1050-E B1, 402-C B1, 1050-P1 B1); inline code in annex prose shows literal
    backticks (69-P2 B11); the problem page shows no annexes and an approach record as a bare
    file link (69-P2 B10, 1050-P2 B3).
32. Guide gaps: `409 node-circular`, `offload-restated-goal`, `pull_request_error`, the
    `/check` rate limit and any polling limit, the approach-record field caps (500/200), the
    bodies of `/defect-claims` (`stmt_ref`, not `node_id`) and `/revision-requests`, the
    `holes[].restates` field, `waiting_on: conflict`, the MCP argument-error shape, which MCP
    tools are "write" tools (`check_lean` is enveloped), the first command block needing a
    `network` clone on the HTTP path, "three rules" that lists five, `proposed_statement` being
    an object, the `closing` block, "nine checks" where a calibration attestation records seven
    (1050-E B7/B9/B14, 69-D B1/B6/B15/B27, 402-B B2/B4, 402-C B2, 402-G B7, 69-C B6/B8, 1050-C
    B2, 69-P2 B8/B9, 1050-W4-1 W1).
33. The Docs page names `POST /proposals`, which is 404 (69-D B20); MCP `get_schema` names a
    plain path that is 404 (1050-W3-1 B1); four MCP descriptions repeat their "Plain path"
    sentence, nine name a git file or "a PR" where a route exists, `get_submission` names the
    wrong path (1050-W3-1 B2, 402-W3-2 B4, 69-W3-1 B3).
34. Problem-page semantics: "closable through its holes: once they are proved" when one proved
    hole was enough (1050-P1 B2, 1050-W4-1 B2); `deps` lists a decomposition's holes as
    dependencies while the docs say holes are not (1050-E B8, 69-D B14); the root shows open
    beside two `stale` status records (69-D B9); every speculative node is captioned "A statement
    the proof needs" (1050-F B6, 1050-W3-1 B5); "speculative" is drawn but not in the key (69-P2
    B5, 1050-P2 B2, 69-W3-1 B6); superseded and circular rows read "Blocked" on the Problems
    index (1050-E B13, 69-P2 B6); a circular node's panel cites the wrong claim, names one of its
    two claims, does not link the claim, and invites work it refuses (69-D B7, 69-E B3/B7);
    tooltip `ready` beside key `open` (69-E B2); a merged partial's author "not recorded"
    (1050-E B10); "acknowledgment of a off-by-one-range finding" (402-W3-2 B5); the informal
    402 statement omits "non-empty" (402-E B2); the glossary's "Explained" maps to no protocol
    word (69-D B22); the Contributors page promises one ledger line per contribution while
    annexes and witnesses earn none (402-W3-2 B2).
35. The problem page does not say what a node *says*, so a planner reading it (the supervisor,
    19:05Z) assigned the already-proved identity on erdos-69 to two agents (69-C B1).
36. The guide's witness-mode statement form cannot preview a narrowed (`proved_binders`) type
    (1050-C B3); a hole's META is `meta/v2` with no `proved_binders`, so "none proved" and "not
    recorded" read alike (402-W4-2).

## Not the network's (recorded so nobody chases them)

- Connection resets and `ws_closed_mid_exchange` on long reads: this container's egress proxy.
- Five container restarts (23:33Z, 23:58Z, 03:59Z, 04:08Z, 04:38Z) killed running agents; the
  disk survived each time.
- `waiting_on` flapping between `merge` and `branch-update` is the queue cycle read at
  different moments, not a bug (2026-09-24 finding 1).
- The `waiting_on` key and `submissions.json`'s `kind` field: the guide is right, agents
  misread (retracted in place: 69-D B2 and others).

## What improved since the 2026-09-24 run

The site updates within 1–3 minutes of a bot commit (was 7.5–15); the bot commit arrives about
five minutes after a merge; `decide +kernel` proofs with 95-value certificates replay in the
gate in under five minutes; a variant can declare a dependency on a merged speculative node and
the precheck says exactly what it waits on at each stage (402-W3-2); `witness_preflight`
matched what the gate then said on every witness this run sent; and the `__` warning is now
dropped for the node-named theorem.
