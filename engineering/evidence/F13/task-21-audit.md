# F13-T21 audit: every service route that opens a pull request on the graph

2026-09-24. The owner's principle, said that evening: "we shouldn't get a pull request at all in
these cases — it should be an error sent back to the user, like reusing theorems, not compiling
etc." Four graph pull requests that day were opened and then failed the gate (two declaration
clashes, one witness that did not compile, one with unacknowledged hazards); all four were variant
proposals opened before the deploy that added the declaration, witness and hazard pre-flights.

This audit lists, for each route that opens (or rewrites) a pull request on the graph, the gate
refusals that route's pull request can meet — read from the gate's mode rules (`opn_gate.modes`),
admission (`opn_gate.admit.default_checks`), step 7 (`opn_gate.steps.witness`), the exhibit
build (`opn_gate.exhibits`) and the graph's `gate.yml` — and whether the service refuses the same
thing before anything is pushed. "Pre-flight" means the hosted fast checker (AXLE) through
`opn_api.checks`; its silence (`unavailable`, `inconclusive`) never blocks a route (§ last).

Legend: **yes** the service refuses it first, deterministically; **pf** refused by a pre-flight
when the checker answers; **by construction** the service writes the thing so it cannot be wrong;
**no** reaches the gate; **n/a** cannot arise on this route.

## `POST /proposals/variant`, `POST /proposals/speculative` (proposal mode, admission)

| Gate refusal | Where | Service before the PR |
|---|---|---|
| path / mode rules, `proposal-incomplete` | classify | by construction (`scaffold.files`, the gate's own builder) |
| one target per PR | workflow | by construction |
| layout: statement not one sorry theorem | admission `layout` | yes (`scaffold` → 400 `proposal-invalid`) |
| `declaration-clash` vs merged node | admission `declaration` | yes (409, F08-T16) |
| `declaration-clash` vs open proposal (merge order) | admission `declaration` | yes (409, F08-T19) |
| same statement already proposed / merged (same node id) | classify (path) | yes (409 copy rule, F07-T35; a merged twin is a declaration clash) |
| `statement-elaboration` (statement does not compile) | admission `statement-axioms` | **was no; now pf** (422 `statement-fails` with Lean's errors on the statement part's lines, F13-T23; the witness, hazard and relation pre-flights all read it). An error only past the statement's lines, or none named, stays `inconclusive` |
| `statement-axiom` (statement rests on an axiom outside the allowlist) | admission `statement-axioms` | **no** — the witness program reports no axioms |
| `witness-type-mismatch` | step 7 | pf (422, F13-T16) |
| `witness-elaboration` (right type, does not compile) | step 7 | pf (422 `witness-fails`, F13-T17) |
| `witness-sorry` from a literal `sorry` token | step 7 | **was no; now yes** (400 `witness-invalid`, F13-T21): a `sorry` compiles on AXLE with a warning, so the pre-flight said `matched` and step 7 refused it |
| `witness-sorry` via a Context dep's restated `sorry`, `witness-axiom` | step 7 | **was no; now pf** (422 `witness-sorry` / `witness-axiom`, F13-T23: the program prints `collectAxioms` of `witness`, held to the target's `axiom_allowlist` in step 7's order) |
| `hazard-unacknowledged` | admission `hazards` (step 6) | pf (422, F13-T20) |
| context not byte-equal to deps | admission `context` | by construction (`scaffold.context_from` over the committed deps) |
| `dep-unknown`, `dependency-cycle` | admission `graph` | yes (404 `dep-unknown`); a new node cannot close a cycle |
| relation: `relation-elaboration`, `relation-direction`, `relation-sorry`, `relation-axiom`, `relation-decl` | admission `relation` | **was no; now pf / yes** (F13-T23): `relation-decl` and a literal `sorry` are 400 before any check; the rest are 422 from `checks.preflight_relation`, which sends the variant's statement, the root's committed statement and `Relation.lean` with the gate's own `expectedRelationType` (`ArtifactType.lean`); `relation_preflight` in the receipt |
| `relation-root-*`, `relation-not-a-variant`, `relation-unlabelled` | admission `relation` | by construction (the scaffold writes the label and root) |
| products lag (node unknown right after merge) | — | n/a (not a refusal of this PR) |

## `POST /proposals/witness` (proposal mode, witness completion, then admission of the hole)

| Gate refusal | Where | Service before the PR |
|---|---|---|
| `witness-not-a-hole`, `witness-filled`, `proposal-incomplete` | `modes.check_witness_completion` | yes (`hole_awaiting_witness`: products say `blocked` / `witness-missing`, else 400 `witness-not-missing`; unknown node 404) |
| a second witness for the same hole (one slot) | merge order | yes (409 copy rule, F07-T35), now **before** the pre-flight so it spends no check |
| `witness-sorry` from a literal `sorry` token | step 7 | yes (400 `witness-invalid`) — **fixed**: now `layout.mentions_sorry`, the gate's own reading; the old `"sorry" in witness` also refused a real witness whose comment names the word |
| `witness-type-mismatch` | step 7 | **was no; now pf** (422, F13-T21) |
| `witness-elaboration` (right type, does not compile) | step 7 | **was no; now pf** (422 `witness-fails`, F13-T21) |
| `witness-sorry` via a Context dep's `sorry`, `witness-axiom` | step 7 | **was no; now pf** (422, F13-T23) |
| declaration, statement axioms, context, graph of the hole | admission | n/a in practice: the hole's statement and Context are the gate's own and already merged; a defect there is pre-existing and no witness can fix it. One that does not compile is now refused 422 `statement-fails` (F13-T23), since its admission would fail whatever the witness |
| `hazard-unacknowledged` | admission `hazards` | n/a: a hole's statement is derived, and step 6 records its findings without refusing (F07-Q19) |

## `POST /defect-claims` and `POST /revision-requests` (append mode, then `opn-gate exhibits`)

| Gate refusal | Where | Service before the PR |
|---|---|---|
| path, file name, `record-invalid` (schema) | `modes.check_append_file` | yes (service writes the path; `appends.validated` against the same schema) |
| class not in D-16's taxonomy | schema / pre-triage | yes (400 `defect-class`) |
| `defect-ref` (stmt_ref names no file / wrong place) | pre-triage | yes (404 / 400, and the service chooses the directory) |
| `defect-line` | pre-triage | yes (400, same line count) |
| `circular-ancestor` | pre-triage | yes (400, F08-T17, same ancestors relation over `graph.json`) |
| second circularity claim on a circular node | — | yes (F08-T18) |
| `exhibit-elaboration` (exhibit does not compile) | `opn-gate exhibits` (sandbox) | **was no; now pf** (422 `exhibit-elaboration` with Lean's errors, F13-T22) for every exhibit that imports only libraries, the target's `Defs` and its own node's `Statement`/`Context` |
| `exhibit-node` (the node's Context does not compile) | exhibits | n/a: a merged node's Context; pre-existing |
| `circular-exhibit`, `circular-direction`, `circular-sorry`, `circular-axiom`, `circular-elaboration` | exhibits (relation program) | **no** — the circularity exhibit is `skipped`, see Q-c; a compile-only check of it would be half the gate's check and could not import the ancestor's modules |
| exhibit importing another node's module | exhibits | **no** (`skipped`): only the gate's staging supplies it, and the checker would see a different file |
| `exhibit-timeout` | exhibits | no: the gate's cap is minutes, the pre-flight's 12 s; a pre-flight timeout is `unavailable` |
| `watcher` request rules | curator mode only | n/a (the service opens appends only) |

## `POST /postmortems`, `POST /annexes`, `POST /approach-records` (append mode)

| Gate refusal | Where | Service before the PR |
|---|---|---|
| path, role, schema, `record-invalid` | `check_append_file` | yes (service writes the path; same schema and caps, F07-R14) |
| annex content-hash name, `annex-too-large` | `check_append_file` | by construction (hash of the file it pushes) / yes (400 at the same cap) |
| identical record already open | merge order | yes (409 copy rule, F07-T35) |
| two different records by one identity in the same second share a file name (`<ts>-<pseudonym>`), and the second can never merge | path collision | **was no; now yes** (409 `record-name-taken`, `Retry-After: 1`, naming the first's pull request, F13-T23): every append route (`appends.append_pr`, so defect claims and revision requests too) takes its path with an atomic counter before the pull request opens, released if it does not open. D-13's name is kept rather than suffixed |
| skeleton citing an unmerged annex | partial mode | n/a on this route (the partial route's concern) |

## `POST /submissions` (proof, counterexample, vacuity, partial, reduction; alternates)

| Gate refusal | Where | Service before the PR |
|---|---|---|
| every step 1–8 refusal | the gate | yes: bound to a **passing precheck** of the same bundle, same identity (`submissions.bound_job`), which runs the pinned gate in full (D-28) |
| `path-forbidden`, `proof-replaces-merged`, `alternate-unproved`, artifact path vs type | classify | yes (`bundles.validate`, `check_placement`) |
| node blocked since the precheck | — | yes (409 `node-blocked`, F06-T6) |
| copy of a merged or open proof | `alternate-duplicate` | yes (409, F07-T35) |
| step 9 (review) | workflow | not a refusal: a wait, reported as `waiting_on` |
| time-of-check vs time-of-merge (a re-pin, a rival's merge, a supersession between precheck and merge) | the gate | no, by nature; a racer's loss is repaired by `racers.py` (below) |

## Service-initiated writes to an open pull request

| Actor | What it pushes | Gate refusals | Service before the push |
|---|---|---|---|
| `racers.py` (F07-T36) | a losing racer's proof moved to `attempts/<ts>-<pseudonym>.alternate.lean` | `alternate-duplicate` | yes (never for a copy of the winner) |
| `withdraw.py` (F07-T43) | closes the PR, deletes the branch | — | n/a |

`POST /precheck` opens job branches on the scratch precheck repository, never on the graph, and
`POST /claims` writes the claim registry only; neither is in scope.

## What this task changed

- **F13-T21** `POST /proposals/witness` (`proposals.post_witness`): the copy rule first, then
  `checks.preflight_witness` over the hole's committed `Statement.lean` (its committed Context
  fetched where it is imported) and the witness; 422 `witness-type-mismatch` / `witness-fails`
  open nothing; `witness_preflight` in the 201. The `sorry` test is the gate's
  `layout.mentions_sorry` (`proposals.check_witness_filled`), and the variant and speculative
  routes now apply it too. Guide ("Witness it", the check paragraph) and the `propose_witness`
  tool description say so.
- **F13-T22** `POST /defect-claims` and `POST /revision-requests` (with an exhibit):
  `checks.preflight_exhibit` sends the exhibit with the node's committed statement, Context and
  `Defs` inlined where it imports them, and refuses 422 `exhibit-elaboration` only when the
  checker says `okay: false` **and** names Lean errors. `exhibit_preflight` in the 201:
  `elaborates`, `inconclusive`, `unavailable`, `skipped`. Guide `defects/` row and both MCP tool
  descriptions say so.

## F13-T23 (the same day)

Q-a, Q-b, Q-c and the same-second name are closed as the rows above say; the circularity
exhibit (`circular-*`) and an exhibit importing another node's module stay `skipped`, and a
checker that cannot answer still never blocks (Q-d unchanged). Evidence:
`engineering/evidence/F13/task-23.txt`.

## Decisions for the owner (Q entries for the lead to log)

- **Q-a — a statement that does not compile at all.** With the witness program never reached,
  `okay: false` plus Lean errors is answered `inconclusive`, and an existing test pins that as the
  design (F13-T16). The errors are deterministic Lean errors, the same the gate's
  `statement-elaboration` would print, so refusing them (say 422 `statement-fails`, or the same
  `witness-fails`) is in the owner's principle's spirit. Not changed here because a test holds it
  and ruling D1 (F13-T17) kept "no verdict" inconclusive; it needs a ruling that `okay: false`
  with Lean errors is a verdict even when the program did not run.
- **Q-b — witness axioms.** Step 7 refuses `witness-sorry` and `witness-axiom` from the witness's
  axiom set; the witness program sent to AXLE reports only types. Adding `collectAxioms` to the
  program (`checks.witness_program`) would close both deterministically; it changes a Lean
  metaprogram, so it wants a lean-tier test, which this container (no elan, no Lean toolchain)
  cannot run.
- **Q-c — relation proofs and circularity exhibits.** The gate's `opn-relation-type` holds a
  variant's relation proof, and a circularity claim's exhibit, to an implication by definitional
  equality and reads its axioms. The same approach as the witness pre-flight (send
  `gate/lean/OpnGate/RelationType*.lean` with the two statements inlined) would cover
  `relation-elaboration`, `relation-direction`, `relation-sorry` and their `circular-*`
  counterparts. A variant with a bad relation proof is today the largest remaining class of
  "opened, then refused". Same lean-tier caveat as Q-b.
- **Q-d — fail closed?** Below.

## When the checker cannot answer: the options

Today, and unchanged by this task: when a pre-flight answers `unavailable` (AXLE down, its
budget spent, no hosted environment for the pin, the identity's check budget spent, a timeout)
or `inconclusive` (no verdict, or `okay: false` with no Lean error to name), the pull request
opens and the gate decides. The receipt says which, so the caller knows the pull request was not
checked.

1. **Fail open (today).** No contributor is ever blocked by a third party. Cost: every AXLE outage
   turns the service back into the old behaviour, where a broken witness or exhibit is a pull
   request and a queue slot (7–8 min a merge on 2026-09-24) before the gate says so; and a
   Mathlib-free target (no hosted environment) is never pre-flighted at all.
2. **Fail closed on `unavailable`, open on `inconclusive`.** A 503 `preflight-unavailable` with a
   `Retry-After`; nothing opens until AXLE answers. Cost: AXLE becomes a hard dependency of every
   proposal, witness and exhibit — a third party's uptime and budget gate the network's writes,
   which D-4 v3.14 calls a courtesy, not a component; Mathlib-free targets could never be
   proposed on, so they would need an exemption (fail open where there is no hosted environment).
   It also makes the identity's own check budget a write limit.
3. **Fail closed on both.** Adds the `inconclusive` cases, which include a statement or witness
   the checker cannot elaborate for reasons of its own (a non-exact environment, a name a newer
   Mathlib renamed). Cost: false refusals that the gate would have accepted, with no appeal but
   waiting for AXLE to change; this is the option most likely to refuse good mathematics.
4. **Fail open, but queue behind the checker.** Keep the pull request as a draft until a later
   pre-flight answers (a retry from the service's own sweep), then mark it ready. Cost: a new
   actor and state on the service, and the merge actor would have to ignore drafts; the most
   work, and the only option that is neither a hard dependency nor a silent pass.

A middle course that costs little: option 1 plus a visible label or pull-request body line
("not pre-flighted: <word>") so the queue can tell unchecked pull requests from checked ones.
