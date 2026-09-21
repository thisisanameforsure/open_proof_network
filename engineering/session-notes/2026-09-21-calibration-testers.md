# 2026-09-21 — three outside-contributor agents on the calibration targets

Mike's instruction: send three agents at the test Erdős problems, have them report bugs and wished
features, then consolidate, verify and prioritise. One agent per target (`erdos-1050`, `erdos-69`,
`erdos-402`), each given only its problem page URL; the 402 agent was told to use the MCP first.
Their running logs are in `engineering/evidence/testers-2026-09-21/`. None read the network source.

## What landed on the graph (PRs #131–#144, no human in any merge)

- `erdos-1050`: witness for `--h1-v2` (#131), annex (#132), postmortem (#135), a one-hole partial
  (#140). The agent showed the hole is equivalent to the irrationality of the tail, so the skeleton
  it sits under moved no mathematics. Nothing of the theorem proved.
- `erdos-69`: annex (#133), a four-hole partial on the hole of a hole (#139), four witnesses
  (#141–#144, gates green, merging in turn when this note was written). Proofs of three of the four
  holes are fast-checked and unsubmitted; the fourth is the real mathematics.
- `erdos-402`: witness for `--h3-v2` (#134), **proof of `--h2-v2` (#136, attested, proved)**,
  postmortem on the root (#138), a variant for `A.card = 2` (#137, merged after 32 min and at
  least eight green gate runs) and its proof (#145, precheck passed, open at 07:23). Proposal to
  first possible precheck of the variant's proof: 36 minutes.

## Verified findings, in priority order

Status: C = confirmed by me (how), P = plausible, not reproduced, X = the agent's reading was wrong.

1. **Green Mathlib pull requests starve behind appends** (all three; C, PR timestamps and
   `merge.yml`). #131 13 min, #134 18, #136 19, #139 20, #140 31, #137 33, against 30–60 s for an
   annex or postmortem. Mechanism, read from `decide()`: the actor takes the oldest *green* pull
   request; one it has just updated is *pending* while its three-minute gate re-runs, so the actor
   passes over it and merges the next green one, which is always a fifteen-second append; that merge
   and then its bot commit each put the Mathlib branch behind again. It merges only when nobody else
   submits for a whole round. This gets worse with every added contributor.
2. **Pre-F08-T13 roots cannot be closed through their holes and nothing says so** (1050, 402; C,
   `Statement.lean` imports Mathlib only). Known limit (log 2026-09-20), but the problem page draws
   the holes as the root's dependencies and offers them as the work. Two agents spent their session
   on holes that cannot finish the target. The cure on the record is a D-8 revision of each root;
   on the site, one line per node.
3. **`∃` binder types are dropped when the gate prints a hole** (69; C, `Holes.lean:91` sets only
   `pp.coercions.types` and `pp.numericTypes`; the live `--h4` statement and every witness slot
   read `∃ N k,`). Two effects: a hole with `∃ m : ℤ` whose type shows only through a coercion is
   refused `hole-not-roundtrip` with a 4 kB message that names nothing; and the witness slot the
   job writes cannot elaborate when the bound variables are unused. Same family as 2026-09-17's
   printing defects. The option that fixes it needs a probe at the pin before code.
4. **A `/check` over 15 s answers a raw 500** (1050; C by reading: `DEFAULT_CHECK_TIMEOUT_S = 60`,
   Lambda `Timeout: 15`, no override in the template; not re-run). `exact?` and any slow tactic hit
   it. API Gateway's own ceiling is 30 s, so the honest budget is under that, with a structured
   timeout answer.
5. **Intermittent 19–75 s stalls on every route** (all three; C, but X on the cause). Reproduced:
   7 of 25 `/health` calls. The whole delay is TCP connect (19.16 s per lost attempt) before any
   request exists; an unrelated API Gateway endpoint in us-east-1 stalled 2 of 25 from this laptop
   and the CloudFront site 0 of 25. So not the service's code, and possibly only this network; all
   three agents shared it. Worth one check from another network before spending on it; fronting the
   api with CloudFront is the fix if it is real for others.
6. **The guide contradicts itself on proving a skeleton's parent** (1050, 69; C). Line 822 (direct
   proof any time) is right: `stage.py:82-90` skips unproved holes (R22). Line 879
   (`dep-unproved` until every hole is proved) is stale from before v3.19.
7. **A precheck runs against products older than a just-merged annex or witness, and says nothing**
   (1050, 69; P, consistent with F06-Q10's pin to `rendered_from`). Costs a whole precheck and the
   failure reads as the contributor's error (`annex-uncited`, `node-blocked` without `Retry-After`).
   The `products-pending` answer exists for proposals only.
8. **MCP refuses the guide's own `tooling` example** (402; C, `mcp/writes.py:194` types `version` as
   string, guide line 557 shows `None`). The message does not name the field.
9. **Guide sentences now false or missing** (C unless noted): the witness slot "says `True` whatever
   the statement is" (line 867; F07-T20 changed it); "about three minutes" is one round, not time to
   merge; "about a second" for `/check`; step 6 does not refuse a gate-written hole's unacknowledged
   hazard (`hazards.py:242`, F07-Q19) and the guide does not say so; the expected witness type for
   `P → ∀ N k, C` is `∃ N k, P` (`WitnessType.lean` telescopes every binder) and the guide's rule
   does not cover it; the HTTP path has no file reads, so it quietly needs a clone or `gh`.
10. **Small service defects** (P, not reproduced): `waiting_on` never reads `branch-update`;
    `submissions.json` has no `waiting_on`; `claims.active[]` has no claim id (schema leaves the
    item open, C); MCP reads answer bare documents while writes answer `{status, body}`;
    `helper-declarations` and `context-restated` lints fire on witnesses and on clean proofs;
    `/check` on a superseded node does not name the replacement; an annex's Lean loses its line
    breaks on the site; a false `unused-binder` finding on `∃ a b : ℕ → ℤ` at step 6.

## Feature wishes, consolidated

Asked for by all three: a merge queue (item 1), and a **witness-type preview** before the pull
request (`/check` with `mode: witness`, or the expected type on `get_node`): today the only feedback
is a 6–20 minute gate round. By two: `get_submission` saying how many times the gate passed and was
overtaken; precheck of a proof while the node's proposal or witness is still open; a per-node
"closable through its holes" flag. By one: a dry run of hole extraction on `/check`; holes closed
only over the binders they use, so a later witness need not re-prove its predecessors (a D-29
question, the owner's); a witness allowed to import proved siblings; Mathlib name search; the MCP
address near the top of the guide; attribution on the node page; a plausibility probe for hole
statements (the 69 agent's first crux was false and fast-checked clean).

## Not the network's

The 69 agent lost its token nonce because two agents shared a scratch directory: my harness, not
the service. Give each agent its own directory next time.

## What was done about it, the same day (Mike's rulings, then test first)

Mike's word on method: "when appropriate make a test that captures the current bug, and use it to
iterate the code until it passes." Each task below has its red run and its green run in its evidence
file; rules also have mutants.

| # | Finding | Ruling | Done | Where |
|---|---|---|---|---|
| 1 | Green Mathlib PRs starve behind appends | fix (the merge queue) | The actor holds the line: an up-to-date gating PR is next and nothing merges past it; a building PR is not updated while a post-merge job is about to move `main`. Replay of #131's morning: merged at second 1080 before, 180 after. **Live on the graph (59d2b38d); the hold rules not yet shown under load.** | F07-T31, Q39 |
| 2 | Old roots cannot close through their holes | the gate allows that one import | A proof may add `import Nodes.«id».Context`, exactly where the service would have put it, and nothing else. Nine of ten live hole parents become closable, no record rewritten. Lean tier: the real gate closes a parent of the live shape. **Live at the re-pin.** | F00-T10, Q13 |
| 3 | `∃` binders printed untyped | fix too | `pp.funBinderTypes` (probed at 4.33.1); the refusal names the hole, says what cures it, carries the text once. **Live at the re-pin.** | F07-T30, Q38 |
| 4 | `/check` over 15 s is a raw 500 | Lambda 29 s, check 20 s | Done and **live**: the agent's `exact?` answers 200 in 17 s; a 40 s sleep answers `504 check-timeout` at 20.8 s with a log id. | F13-T13, Q16 |
| 5 | 20 to 75 s stalls | track down the cause | Lost SYNs on the path from this network to API Gateway: 8/40 from the laptop, 0/200 from a hosted runner, 0/40 to every other AWS front end. Not the service. CloudFront in front of the api is the cure if it is ever seen elsewhere: Mike's call, nothing changed. | `evidence/F05/connect-stalls-2026-09-21.txt` |
| 6 | The guide's `dep-unproved` sentence | an agent must be able to prove the root if it finds a proof | It always could (R22); the sentence is gone and the behaviour is a test beside the words. | F10-T12, Q18 |
| 7 | Precheck against stale products | (my proposal, approved with the plan) | `409 annex-pending`, `400 annex-unknown`, `409 products-pending` before any job exists; the same for a hole whose witness just merged, on precheck and claim. **Live.** | F06-T8, Q13 |
| 8 | MCP refuses the guide's `"version": None` | fix | Nullable, capped as the endpoint caps; a refused argument is named. **Live.** | F09-T10, Q12 |
| 9 | Guide sentences | update docs | Done, with the merge queue, witness mode, the budget, the refusals, the import rule, the MCP address near the top. Graph copy e88abf3a. | F10-T12 |
| 10 | Small findings | reproduce first | Three real and fixed (`context-restated`, no `node-superseded` warning, `unused-binder` on a function type); three by design, now guide sentences; one not reproduced; **one is Mike's: a claim id on the frontier is a `claims/v2` bump or a new `GET /claims` route.** | F13-T15, F02-T8; `evidence/F13/task-15.txt` |
| + | Witness-type preview | yes | `mode: "witness"`: the gate's own `WitnessType.lean` sent through the hosted checker. **Live**, after its first deployed call found a defect the lean tier could not (an empty witness on a node with a Context). On `erdos-69--h2-v2--h1-v2--h4`: expected type in 1.3 s, the merged witness `matches: true`. | F13-T14, Q17 |
| + | "Closable through its holes" flag | yes | `closing` block on `get_node`; a line on the panel of every open node that has holes (8 panels on the live graph), with the import line where the statement predates it. One function decides both. | F04-T25, F09-T11 |

Still open after this sitting: the hold rules seen under load (the next building pull request opened
beside an append); the claim id (Mike's); CloudFront for the api (Mike's, and only if the stalls
are ever seen from another network); the wishes not asked for (`get_submission` rounds, precheck of
a proof while its proposal is open, a hole-extraction dry run, independent holes, which is a D-29
question).
