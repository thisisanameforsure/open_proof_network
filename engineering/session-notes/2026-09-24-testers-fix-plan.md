# Plan: fixing what the 2026-09-24 testers found (for review)

> **Status, 2026-09-24 evening.** Built, each red first with its evidence:
> - A1, A10, A11, A14 (F13-T17 to T20; A14's lean-tier equality test runs in CI).
> - A2, A6, A7 (F07-T39, T41, T42) and A8 (F05-T15).
> - A3 (F05-T14, with `GET /claims/mine`) and A12 (F07-T43).
> - A4, A13 (F08-T18, T19), A5 (F07-T40) and A9 (F09-T13).
> - B1 (F04-T26), B2 (F06-T9), B3 (seen live) and the guide (F10-T14).
>
> Waiting on Mike's approval of `2026-09-24-decisions-amendment-v3.22.md`: B5 and C1. Waiting on
> the re-pin: B2, and the guide's graph copy.

Source: `engineering/session-notes/2026-09-24-calibration-testers.md` and the six logs in
`engineering/evidence/testers-2026-09-24/`. **Out of scope, by Mike's word:** merge-queue throughput
and everything downstream of it (queue position, ETA, `waiting_on` flapping between `merge` and
`branch-update`). He is handling that in another session.

Nothing here is built yet. The plan is written for review: the decisions it needs are in §1, and
each work item says which decision it waits on.

## How every item is built (the test-heavy part)

1. **Red first, in its own file.** Each finding gets `api/tests/test_finding_<slug>.py` or
   `gate/tests/test_finding_<slug>.py`. The module docstring tells the story (who found it, when,
   the request, what came back), the mechanism, and the task number. The test asserts the *correct*
   behaviour. It is committed as `xfail(strict=True)` naming the fix (conventions §2), so the suite
   stays green and the fix flips it.
2. **The red run must fail on the defect**, not on a missing name (log, 2026-09-21). New symbols
   are looked up with `getattr` inside the test body, or the seam is added at today's value first.
   Each red run is captured in `engineering/evidence/FXX/task-N.txt`.
3. **Every rule gets its mutants.** For each new rule, one pytest plugin (`-p`, monkeypatching in
   memory, as in F11-T7) weakens it, and the evidence shows at least one test fails under each
   mutant. This proves the tests would catch a regression, not just that they pass.
4. **Pin what must not change.** Every item also carries the tests that were already green and
   must stay green (the neighbouring behaviour), listed below as "guards".
5. **Seams are tested on both sides.** Anything touching the store runs on the both-stores fixture
   (`test_pending_submissions.store`). Anything touching the host runs on `FakeGitHost` *and* on the
   `test_githost_seam.py` HTTP script.
6. **Docs are tests** (log, 2026-09-11). Every guide sentence this plan adds is asserted in
   `gate/tests/test_finding_guide_tester_0924.py` against the code constant it describes. For
   example, the guide's "200 kB" is read against `config.DEFAULT_CHECK_MAX_BYTES`, so the two cannot
   drift.
7. **Deployed routes are called live after deploy** (log, 2026-09-21: "call the route, not the
   composer"). Each item's evidence ends with one live request against `api.openproofnetwork.org`.
   The request is an inert or read-only probe where possible, and a probe that writes must clean up
   what it opened.

Gate: `make verify` before every commit, and `make verify-lean` in CI for anything touching
`gate/`.

## 1. Decisions

**Rulings, 2026-09-24 (Mike):**

| # | Ruling |
|---|---|
| D1 | A witness that does not compile is refused (`422 witness-fails`). |
| D2 | A defect claim of the same class is refused when one is merged, and named in the receipt when one is open. |
| D3 | `GET /claims/mine`, authenticated, with an MCP `list_my_claims` tool. Public creation times are deferred. |
| D4 | One circularity claim takes the **whole path** from the ancestor A down to the hole H off the frontier. A node in between leaves only where the other pieces along the path are proved, so its equivalence to A is established. A stays open and claimable, and says "a decomposition beneath this was circular (claim #N); prove it directly or decompose it differently". The target is never closed. **B5.** |
| D5 | Add `DELETE /submissions/<id>` (A12). |
| D6 | Filter the naming-linter warning (A10). |
| D7 | Skip. B4 is dropped and CI stays as it is. |
| D8 | The hazard checkers run through AXLE, as witness mode already runs the gate's own Lean. Unacknowledged hazards on a proposal are refused before the pull request opens, and `/check` gets a `hazards` mode. **A14.** Precheck against a *pending* node stays deferred with the queue work. |
| D9 | Draft the amendment: a hole's witness covers only its unproved hypotheses, and the gate supplies the proved ones from the merged skeleton. The doc change is approved before any code. **C1.** |

The options as first put to Mike are kept below for the record.


| # | Question | Options | My recommendation |
|---|---|---|---|
| D1 | A proposal's witness has the right *type* but does not compile. | (a) refuse `422 witness-fails`, naming the errors; (b) open the pull request and say `inconclusive` | **(a).** AXLE runs the pin's own toolchain and step 7's own metaprogram, so the gate would refuse it anyway, one queue slot later. A timeout still says `unavailable`, never a refusal. |
| D2 | A defect claim of the same class on the same node | (a) refuse when one is merged, warn when one is open; (b) warn only; (c) leave as is | **(a).** A second merged circularity claim adds nothing, and an open one is worth knowing about. By D-25 these are not copies, so this is a rule about defects, not about duplicates. |
| D3 | Claim ids and creation times, and "my claims" | (a) `claims/v2` (hash-pinned bump, gate consumers); (b) new authenticated `GET /claims/mine` (a D-35 route); (c) defer | **(b)** for "my claims". **(c)** for public creation times; the receipt change in A3 covers most of the need. |
| D4 | A circular node reads `status: ready, cause: circular` | (a) guide sentence: read `cause`; (b) `graph/v4` with a `circular` status | **(a).** The schema already allows the cause, and a status bump reaches every consumer (log, 2026-09-11). |
| D5 | Withdraw one's own pull request (three agents asked) | (a) `DELETE /submissions/<id>`: holder only, closes the PR, never merged ones; (b) defer | **(a).** It is a new D-35 write route, so it is yours to approve. |
| D6 | Filter Mathlib's naming-linter warning on gate-generated `__` names in `/check` | (a) filter only when the name is the node's own gate-generated one; (b) leave | **(a)**, low priority. |
| D7 | Skip the network repo's Lean CI tier for docs-only diffs | (a) job-level skip that still reports; (b) leave | **(a).** Conventions §2 says "every push", so this edits a convention. |
| D8 | Precheck a proposal (hazards before the PR), and precheck against a pending node | (a) spec it as a new feature; (b) defer | **(b).** It needs a sandboxed admission run, which the service cannot do. The guide says so, and A11 covers the cheap half. |
| D9 | Proved `have`s should not become witness obligations of later holes | D-29 question | Yours; this plan does not touch it. |

## 2. Service fixes (live when the network pushes to `main`, no re-pin)

### A1. The witness pre-flight reads `okay` (F13-T17, Q20) — D1: refuse
- **Fix:** `checks.preflight_witness` (checks.py ~L715): `matched` only when `matches` is true and
  `verdict(body)` is true. When `matches` is true and `okay` is false: per D1. When `okay` is null
  (`user_error`): `inconclusive`, as today.
- **Red:** `test_finding_witness_preflight_okay.py`
  - `test_a_right_typed_witness_that_does_not_compile_is_not_matched`. FakeAxle replies
    `answer(MATCH, okay=False)` with a `decide` error; under D1(a) it expects 422 `witness-fails`
    with the error text and no pull request opened (`githost.pulls` empty).
  - `test_the_refusal_names_the_checker_errors_and_the_log_id`.
  - `test_a_timeout_is_still_unavailable_never_a_refusal`.
  - `test_speculative_and_variant_routes_agree`.
  - `test_mcp_propose_variant_carries_the_same_refusal`.
- **Guards:** all of `test_finding_witness_preflight.py` and `test_check_witness_mode.py`.
- **Mutants:** drop the `okay` read; treat null as false.
- **Docs:** guide lines 208–218 get the new outcome, plus a sentence that `/check` in witness mode
  reports `okay` and `witness.matches` separately and a witness passes only when both hold.

### A2. `GET /submissions.json` answers in seconds, not tens of seconds (F07-T39, Q47)
- **Fix:** `pending.snapshot` reconciles its records concurrently on a bounded pool (8 workers).
  `HttpxGitHost` reuses one `httpx.Client` per `get_pull_request` instead of four. `racers.convert`
  stays per record; a per-PR lock keeps a racer from being converted twice.
- **Red:** `test_finding_submissions_cold_latency.py`
  - `FakeGitHost` gains `pull_latency_s` (a sleep on `get_pull_request`).
  - `test_twenty_five_open_records_answer_within_four_lookups_of_time`: at 0.2 s per lookup, the
    snapshot finishes under 1.2 s (it takes 5 s today).
  - `test_the_concurrent_snapshot_equals_the_serial_one`: same records, same order, same fields.
  - `test_a_losing_racer_is_converted_once_under_concurrency`: `push_branch` is called exactly once.
  - `test_one_failing_lookup_leaves_its_row_listed_and_the_rest_reconciled`.
  - Seam test: `test_get_pull_request_opens_one_client`.
- **Guards:** `test_pending_submissions.py`, `test_finding_stale_open_submissions.py`,
  `test_finding_racer_alternate.py::test_the_snapshot_converts_too`,
  `test_mcp_pending_submissions.py`.
- **Live:** a cold `GET /submissions.json` with more than 15 open, timed, under 5 s.

### A3. Claims: one per holder per node, and the receipt says who else is there (F05-T14, Q15)
- **Fix:** in `claims.post_claims`, a second `POST /claims` by the same identity on the same node
  answers `200` with the existing active claim, not a new one. The receipt gains `others`: the
  other active holders (`pseudonym`, `expires`), from `registry()`. This needs no schema change,
  because a receipt is not a product. The MCP `claim_node` description says so.
- **Red:** `test_finding_claim_twice.py`
  - `test_the_same_holder_claiming_twice_gets_the_same_claim` (one active entry in `claims.json`).
  - `test_after_release_a_new_claim_is_a_new_id`.
  - `test_an_expired_claim_does_not_count_as_held`.
  - `test_the_receipt_lists_other_active_holders_and_not_the_caller`.
  - `test_the_receipt_omits_expired_and_released_holders`.
  - `test_racing_is_still_allowed_across_holders`.
- **Guards:** `test_claims.py` (`test_racing_allowed`, the cap tests), `test_rejections_claims.py`,
  and the both-stores fixture.
- **D3(b), approved:** `GET /claims/mine` gets its own red file: holder-only, lists ids, 401 without a
  bearer, a bijection row and an MCP `list_my_claims` tool.

### A4. Defect claims know the node's state (F08-T18, Q30) — D2: refuse if merged, name if open
- **Fix:** `requests.post_defect_claims` keeps the `node_facts` it already reads (it is discarded
  today, requests.py ~L162). A `circular-decomposition` claim on a node whose cause is `circular`
  answers `409 node-circular`, in `claims.circular()`'s words. An open defect claim of the same
  class on the node adds `also_open: [{pr_number, pseudonym}]` to the 201 body.
- **Red:** `test_finding_defect_claim_known_state.py`
  - `test_a_circularity_claim_on_a_circular_node_is_refused_with_the_merged_claims_path`.
  - `test_an_open_same_class_claim_is_named_in_the_receipt`.
  - `test_a_different_class_on_a_circular_node_is_still_accepted`.
  - `test_a_claim_on_another_node_sees_nothing`.
- **Guards:** `test_finding_circular_claim.py`, `test_claims_defect.py`,
  `test_finding_duplicate_submissions.py`.

### A5. A proof submission says what else is on the node (F07-T40, Q48)
- **Fix:** the `POST /submissions` 201 body gains `rivals` (open proof submissions on the node:
  `pr_number`, `pseudonym`). If the node is already proved, it also gains
  `node_proved: true, becomes: "alternate"`. It never refuses; racing stays allowed (D-25).
- **Red:** `test_finding_submit_rivals.py`
  - `test_an_open_rival_proof_is_named`.
  - `test_a_proved_node_says_the_proof_becomes_an_alternate`.
  - `test_a_node_with_nothing_open_says_nothing` (no keys, not empty lists).
  - `test_mcp_submit_proof_passes_the_keys_through`.
- **Guards:** `test_finding_duplicate_submissions.py` (a copy is still refused),
  `test_submissions_alternate.py`.

### A6. A proposal's submission shows the proposed statement (F07-T41, Q49)
- **Fix:** `GET /submissions/<id>` for a `speculative`/`variant` record adds a top-level
  `proposed_statement` (the branch's `Statement.lean` at the PR's `head_sha`, capped at 16 kB).
  It sits outside the `submission` document, so the pinned equality between `submissions.json`
  entries and per-id documents still holds. The MCP adapter schema `get_submission/v1` is reshaped
  in place (F09-Q5).
- **Red:** `test_finding_proposal_statement.py`
  - `test_a_variant_submission_carries_its_statement_at_the_head_sha` (`FakeGitHost.files_at`).
  - `test_a_proof_submission_has_no_statement_key`.
  - `test_a_host_failure_gives_null_with_the_reason`.
  - `test_the_list_entry_still_equals_the_document`.
  - `test_mcp_get_submission_schema_validates_the_new_shape`.

### A7. `runs[].jobs` has one shape, open or closed (F07-T42)
- **Fix:** `githost.get_pull_request` always emits `jobs` (`[]` when not fetched).
  `pending.document` normalises stored `final_state`s written before the change, so old merged
  records read the same.
- **Red:** `test_finding_runs_jobs_shape.py`
  - `test_a_merged_pull_request_carries_jobs_on_every_run`.
  - `test_an_open_failed_gate_run_keeps_its_fetched_jobs`.
  - `test_a_record_closed_before_the_change_reads_with_jobs`.
  - A seam test on the HTTP script.
- **Guards:** `test_githost_seam.py::test_a_failed_gate_run_on_an_open_pull_request_carries_its_jobs`,
  `test_finding_waiting_on_lag.py`.

### A8. `waiting_on: products` for a merged annex or witness too (F05-T15, Q16)
- The tester's "merged proposal" was an annex. The code matches the guide for proposals, but a
  merged annex or witness reads `null` while precheck answers `409 products-pending`.
- **Fix:** `pending.waiting_on_products` also covers an annex whose hash the products do not carry
  yet (reuse `precheck.awaits_render`) and a witness whose node still reads `witness-missing`.
- **Red:** `test_finding_waiting_on_products_appends.py`
  - `test_a_merged_annex_not_yet_rendered_waits_on_products`.
  - `test_it_clears_once_rendered`.
  - `test_a_merged_witness_waits_until_the_node_is_no_longer_witness_missing`.
  - `test_a_merged_postmortem_never_waits` (nothing depends on it).
  - `test_a_graph_read_failure_leaves_null`.
- **Guards:** `test_finding_node_pending.py`.

### A9. MCP descriptions name the schema versions the tools write (F09-T13)
- **Fix:** the `get_schema` description (reads.py ~L538) names `defect-claim/v3` for the
  circularity class. `file_defect_claim` says it writes v1, and v3 when `ancestor` is given.
- **Red:** `test_finding_mcp_schema_versions.py`
  - `test_every_schema_id_named_in_a_tool_description_exists_in_gate_schemas`.
  - `test_file_defect_claim_names_every_version_requests_writes`, which reads `DEFECT_SCHEMA` and
    `CIRCULAR_SCHEMA` from `requests.py` rather than hard-coding them.

### A10. `/check` drops the naming-linter warning on gate-generated names (F13-T18) — D6: yes
- **Fix:** drop a warning only when it is Mathlib's naming linter *and* the flagged name is the
  node's own gate-generated declaration (`<id>` with `-` becoming `_`). All other warnings pass
  through verbatim.
- **Red:** `test_finding_check_naming_noise.py`
  - `test_the_gate_generated_name_warning_is_dropped`.
  - `test_a_contributors_own_double_underscore_name_still_warns`.
  - `test_other_warnings_are_untouched`.
  - `test_the_call_log_counts_what_axle_said_not_what_was_shown`.

### A11. `/check` refusals and guide cover the limits (F13-T19)
- **Fix:** the `413 content-too-large` message says what to do (make the case split cheaper; no
  helper declarations). No behaviour changes; this is the text half of B5.
- **Red:** extend `test_checks.py` with `test_the_413_names_the_limit_and_the_remedy`.

### A13. A proposal that redeclares an open or merged node's theorem is refused before it opens (F08-T19, Q31)
- **Found at the 16:30Z queue check.** Graph #189 and #198 (402-MCP's |A| = 6 and 7 variants)
  failed at the gate with `declaration-clash`: the other agent's #188 and #190 had already declared
  `Opn.erdos_402_card_six` and `Opn.erdos_402_card_seven`. The service could see this before
  opening the PR. The texts differed, so the copy rule rightly let them through.
- **Fix:** before opening, the proposal routes run the gate's own declaration check (the string
  comparison F08-Q18 moved to the fast tier) against:
  - merged nodes (from the products);
  - open proposals (the branch `Statement.lean` of each open `speculative`/`variant` record).

  A clash answers `409 declaration-clash`, naming the holder and, if open, its PR.
- **Red:** `test_finding_proposal_declaration_clash.py`
  - `test_a_name_held_by_a_merged_node_is_refused`.
  - `test_a_name_held_by_an_open_proposal_is_refused_with_its_pr`.
  - `test_a_revision_that_supersedes_the_holder_is_allowed` (D-8).
  - `test_a_fresh_name_opens`.
  - `test_the_service_and_the_gate_agree` (the same function, imported, not re-implemented).

### A14. Hazards are checked through AXLE before a proposal opens, and `/check` has a hazards mode (F13-T20, Q21; F02 owns the checkers) — D8
- **Why it is possible:** the checkers (`gate/lean/OpnGate/Hazards*.lean`, about 400 lines) import
  only `Lean`. So the service can inline them with a few lines that ask one question of one
  declaration, exactly as `checks.witness_text` inlines `WitnessType.lean`. The findings come back
  on one tagged info line.
- **Fix:**
  - `checks.hazards_text` composes the program.
  - `POST /check` gains `mode: "hazards"`, answering
    `{findings: [{checker, location}], checkers}`. It runs the checkers the target's
    `gate-spec.json` names.
  - `POST /proposals/variant` and `/speculative` run it first. A finding not covered by the
    proposal's `acknowledged_hazards` is refused `422 hazard-unacknowledged`, with the gate's own
    finding shape. If AXLE cannot answer, the proposal opens as today and step 6 remains the
    verdict.
  - Charged and logged like every check (F13-R8, R9).
- **Red:** `api/tests/test_finding_hazards_preflight.py`
  - `test_the_program_sent_is_the_gates_own_source` (hash of the inlined files equals the gate's).
  - `test_an_unacknowledged_div_zero_is_refused_before_a_pull_request_opens`, replaying #202's
    statement and finding.
  - `test_an_acknowledged_finding_opens`.
  - `test_only_the_targets_checkers_run`.
  - `test_axle_unavailable_opens_as_today`.
  - `test_check_hazards_mode_answers_the_findings`.
  - `test_mcp_propose_speculative_node_carries_the_refusal`.
- **Lean tier (the check that matters):** `gate/tests/test_hazards_through_axle_text_lean.py` runs
  the composed text with the local toolchain on every fixture statement in `test_hazards_lean.py`.
  It asserts the findings equal `opn-hazards`' own, finding for finding. This is how we know the
  inlined program is the gate's checker and not a lookalike.
- **Live:** `/check` hazards mode on #202's statement returns its div-zero findings.
- **Docs:** guide line 272 ("runs none of the hazard checkers") is rewritten.

### A12 (D5: yes). Withdraw one's own pull request (F07-T43, Q50)
- **Fix:** `DELETE /submissions/<id>`: holder only, closes the pull request and deletes its branch,
  `409` if it has merged, idempotent on an already closed one. Adds an MCP `withdraw_submission`
  tool and a bijection row.
- **Red:** `test_finding_withdraw.py`
  - `test_the_holder_closes_their_open_pull_request`.
  - `test_another_identity_gets_403`.
  - `test_a_merged_submission_gets_409`.
  - `test_twice_is_harmless`.
  - `test_the_snapshot_drops_it`.
  - `test_the_merge_actor_never_sees_a_withdrawn_branch`: a static check of `merge.yml`'s filter
    against a closed PR.
- **Live:** withdraw a probe PR opened on the tutorial node, then read it back closed.

## 3. Gate and site (the gate part is live only at a re-pin, which is Mike's act)

### B1. Circular reads plainly (F04-T26, Q28)
- **Site fix:** `circular` joins `LEGEND_EXTRA`, `GLOSSARY` and the Docs state map keys, with its
  own dot style instead of the `blocked` ring.
- **Red:** in `site/tests/test_graph_legend.py`, generalise the guard to
  `test_every_cause_the_gate_can_derive_has_a_key_entry`, which iterates every `CAUSE_*` constant
  in `opn_gate.graph`. It fails on `circular` today, and it would have caught this the day the
  cause was added.
- **Also red:** `test_finding_circular_key.py`
  - `test_a_circular_node_is_drawn_with_the_circular_style`.
  - `test_the_glossary_explains_circular_and_names_the_defect_claim`.
- **Guards:** `test_finding_circular_label.py`, `test_finding_status_cause.py`, `test_docs_states.py`.
- **Evidence:** screenshots at 1440 and 390, with Playwright `getBBox` label checks for the state
  map (log, 2026-09-19).
- **Site goldens:** regenerated in the same commit.
- **Gate:** no change under D4(a).

### B2. The precheck answer carries the holes' closed types (F06-T9, Q14)
- **Fix:** `gate/precheck/job.py` adds `holes: [{name, closed_type, index}]` from
  `ctx.data["artifact"]` to `result.json` when step 4 found a partial. First check whether the
  result's signature covers the whole document (`precheck.verify_result`). If it does, the field
  goes inside and is signed; it is never bolted on outside.
- **Red:** `gate/tests/test_finding_precheck_holes.py`
  - A fast tier with the fake toolchain's artifact report:
    `test_a_partial_precheck_names_each_hole_with_its_closed_type` and
    `test_a_proof_precheck_has_no_holes_key`.
  - The api passes it through: `test_precheck.py::test_a_done_job_serves_the_holes`.
  - Docker tier: extend `test_precheck_job_docker.py` with a two-hole skeleton. The closed type
    printed must equal the one the post-merge job would write; this is the same printer, asserted
    by string.
- **Live:** at the next re-pin, one precheck of a two-hole skeleton on the tutorial variant.

### B3. A second partial on a decomposed node (verification only; seen live)
- F07-T21 already numbers holes after the earlier ones, and the existing tests cover it.
- **Seen live 2026-09-24:**
  - #196 merged 15:04Z; its post-merge job (`gate: #196 pass`, bb02ddab) wrote `--h2`, after the
    existing `--h1`.
  - #199 merged 15:26Z; its job (`gate: #199 pass`, 2421b927) wrote `--h3` and `--h4`.
- **Work:** one fixture test in exactly that shape, with the two commits recorded in the evidence:
  `test_postmerge_apply.py::test_a_second_skeleton_on_a_node_with_holes_numbers_after_them`.

### B4. (Dropped by D7.) The network CI skips the Lean tier for docs-only diffs
- **Fix:** in `ci.yml`, a first job computes whether the diff touches only `engineering/**`,
  `docs/**` or `*.md` outside `gate/agents/`. `verify-lean` gets `if: needs.changes.outputs.code ==
  'true'`, so it reports `skipped`, which GitHub counts as passed for a required check. The job
  name is unchanged (log, 2026-09-10).
- **Red:** `gate/tests/test_finding_ci_docs_only.py`, a static read of `ci.yml`:
  - `test_verify_lean_is_skipped_not_absent_for_docs_only`.
  - `test_the_job_names_are_unchanged`.
  - `test_the_guide_is_not_docs_only`: `gate/agents/AGENTS.md` is tested by the walkthrough, so
    it counts as code.
  - `test_a_push_to_main_always_runs_both_tiers`.
- **Live:** one docs-only PR whose `mergeable_state` reads `clean` with the tier skipped.

### B5. One circularity claim takes the whole path off the frontier (F08-T20, Q32; decisions amendment to D-16) — D4
- **Rule (derive, never rewrite; F08-T10's principle):** a merged `circular-decomposition` claim on
  H with ancestor A makes a node X strictly between A and H `cause: circular` when both hold:
  - X lies on the dependency path from A down to H;
  - every other hole of every skeleton on that path is proved.

  Nothing on disk changes, and reverting the claim's commit restores every node. A gets a note,
  not a status. Its `graph.json` entry carries `circular_below: [<claim path>]`: a new optional
  field, so `graph/v4` or the open `cause` object. Price this against HASHES before choosing;
  prefer the form with no schema bump.
- **Amendment first:** D-16's circularity paragraph says the claimed hole leaves the frontier. The
  amendment extends that to the established path, with this rule's two conditions. Drafted for
  Mike's approval before code.
- **Red:** `gate/tests/test_finding_circular_path.py`, on a fixture built in erdos-69's live shape
  (root → h2 → h2--h1 → h2--h1--h4, with h1 proved).
  - `test_one_claim_on_the_deepest_hole_takes_the_whole_chain_off_the_frontier`.
  - `test_a_node_whose_sibling_hole_is_unproved_stays_on`.
  - `test_it_leaves_once_that_sibling_is_proved` (no new record is needed).
  - `test_the_ancestor_stays_claimable_and_carries_the_note`.
  - `test_reverting_the_claim_restores_every_node_byte_for_byte`.
  - `test_a_proof_of_a_path_node_is_still_accepted` (D-16: a proof of it would prove A).
  - `test_the_live_erdos_69_record_is_unchanged` (its three claims already cover the chain).
- **Mutants:** ignore the sibling-proved condition; include A itself; stop at H's parent.
- **Site:** the ancestor's panel shows the note with a link to the claim, with a screenshot.
- **Live:** at the re-pin, which is Mike's act.

## 3b. The protocol change (drafted for approval, then built)

### C1. A hole's witness covers only its unproved hypotheses (decisions amendment to D-29 and D-4 step 7; F07-T44, Q51) — D9
- **Today:** a hole is closed over every earlier `have` in scope (F11-Q22), so its witness must show
  every one of them can hold at once. Facts the skeleton already *proved* must be proved again: 250
  lines on erdos-1050's #196, and the whole of `h3`/`h4` on the on-ramp in September.
- **Amendment (drafted first, approved before code):**
  - A hypothesis that came from a `have` the skeleton proves is discharged by the gate, from the
    proof in the merged assembly. The witness exhibits only the hypotheses that came from holes.
  - The hole's *statement* does not change. It stays closed over everything, so D-31
    finalisation and the round trip are untouched. Only step 7's expected type changes.
- **Build:**
  - `holeReport` marks each binder of the closed type as `proved` or `hole`.
  - `WitnessType.lean` computes the expected type over the `hole` binders only, and the proved
    ones are instantiated with the assembly's terms.
  - The post-merge job records which binders were proved, in the hole's `META.yaml`, which it
    already writes.
  - Step 7 reads that record.
- **Red, lean tier where the Lean is:**
  - `gate/tests/test_finding_witness_proved_haves_lean.py`
    - `test_a_hole_after_a_proved_have_asks_only_for_the_unproved_hypotheses` (fixture: one proved
      `have`, one hole, one later hole).
    - `test_a_hole_after_a_hole_still_asks_for_that_hole`.
    - `test_the_statement_text_and_hash_are_unchanged`.
    - `test_an_old_hole_with_no_record_keeps_todays_expected_type`: nodes merged before the
      change are unaffected, whatever pin they were witnessed under.
  - Fast tier: `test_postmerge_apply.py::test_the_hole_meta_records_which_binders_were_proved`.
  - api: `/check` witness mode and the A1 pre-flight use the same expected type, via the shared
    `WitnessType.lean`.
- **Live:** at the re-pin. The first witness filed on a new hole after a proved `have` is the
  evidence.

## 4. The guide and other documentation (F10-T14, Q20)

`gate/agents/AGENTS.md`, copied byte for byte to the graph at the next re-pin
(`test_graph_copy_is_identical`). Each sentence below is asserted in
`gate/tests/test_finding_guide_tester_0924.py` against the constant or behaviour it describes.

| Passage (current line) | Change |
|---|---|
| `/check`, L193–197 | State the limits: 200 kB of content (`DEFAULT_CHECK_MAX_BYTES`) and 20 s (`check_timeout_s`). Lean's 200000 heartbeats count per declaration, and a tactic-level `set_option maxHeartbeats` does not lift them. A `set_option` before the theorem is refused as `proof-not-statement` (F00-R19). A long case split must be made cheaper, for example one `have` per case with `exact` at the leaves. |
| Witness pre-flight, L208–218 | A1's outcome. `/check`'s witness mode passes only when `okay` and `witness.matches` both hold. |
| Tutorial node, L52–67 | For an HTTP-only agent, give the node's path (`targets/tutorial/nodes/tutorial-and-swap/`) and how to read it at `rendered_from` on the raw host. A test asserts the path exists in the fixture and in the live graph copy. |
| Claims, L322–323 | Claiming twice returns the same claim. The receipt lists other holders; read it before starting. (A3) |
| Submissions, L595–615 | `products` covers merged annexes and witnesses (A8). `runs[].jobs` is always present (A7). A proposal's record shows its statement (A6). A proof's receipt names rivals (A5). |
| `defects/` row, L441, and Skeletonization, L881–887 | Name the circularity class and its `ancestor` and exhibit. Check the node's `cause` first. A second claim is refused or named per D2 (A4). A circular node keeps `status: ready` and carries `cause: circular`, so read `cause` (D4). |
| Products, near L289 | The service's `rendered_from` is the commit it read the tree at, which can be newer than the committed file's own `rendered_from` (the F05-T13 overlay). |

Also updated in the same commits:
- Each spec's `Tasks:` ledger and Q table: F05, F06, F07, F08, F09, F10, F13 and F04.
- `engineering/specs/index.html` status cells.
- `site/tests/test_finding_docs_agents_md.py`, if a heading moves.
- The log in `engineering/CLAUDE.md`, one entry at the end of the sitting.

## 5. Order, and what is Mike's

1. §1 decisions.
2. One commit of all red tests, strict xfail (`evidence: the 2026-09-24 findings as red tests`).
   The suite stays green; each later fix flips its own tests.
3. A1, A3, A7, A9, A11: small, independent. Then A2, A4, A5, A6, A8, A13, A14. Then A10 and A12.
   One commit per task (`FXX-Tn:`), each with its red run, green run and mutant runs in the
   evidence.
4. B1 (site), B3 (verification).
5. Drafts of the D-16 (B5) and D-29 / D-4 step 7 (C1) amendments to Mike. Then B5 and C1,
   test first, which reach the graph at the re-pin.
6. F10-T14 (the guide) last, so it describes what shipped.
7. Push to `main`, which deploys the service. Then the live probes for A1–A14.
8. **Mike's:** approving the two amendments, and the graph re-pin that makes B2, B5, C1 and the
   guide copy live. Their live checks come after it.

**Estimate:** about 60 new tests across 14 files plus 3 static CI tests, and 4 extended guard files.
The fast tier grows by under 10 s; B2 adds one docker-tier case (about 3 min).
