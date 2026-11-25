# mcpfix WB2 — service fixes behind the MCP (2026-11-25)

Worktree /Users/mikehiggins/Desktop/repos/opn-mcpfix-wb2, branch mcpfix-wb2, from origin/main ae6c445c.

## Item 6 — messages
- red: api/tests/test_mcpfix_wb2_messages.py, 14 failed / 3 passed (wb2-6-red.txt), each on the message.
- fix: `stewards.github_login(held, act)` (act now required; 11 callers name their act); a tutorial
  proof missing/empty/non-string `job_id` or `nonce` is `400 proof-invalid` naming the field
  (`details.field: proof.<name>`), checked before the token-start rate limit counts the request.
- green: 17/17 in the new file; 227 + 124 in the touched route and token suites.

## Item 4 — submission filters
- red: api/tests/test_mcpfix_wb2_filters.py, 4 failed / 1 passed (wb2-4-red.txt): kind=nonsense and
  target=elsewhere answered 200 [], and the union seam was empty.
- fix: `pending.SUBMISSION_KINDS` (31 kinds); `kind` outside it and `words` is `400 filter-unknown`
  listing them (`details.accepted_kinds`); `target` not in targets/index.json is `404 not-found`
  (`pending.known_filter_target`). The old test line asserting `?target=elsewhere == []` was restated.
  A guard test scans every `kind="..."` and `KIND* = "..."` in api/opn_api so a new kind cannot be missed.
- green: 5/5 new; 233 in the submissions/MCP suites.

## Item 5 — drafted_with and gloss-no-latex
- MEASURED (wb2-5-drafted-with-measure.txt): live graph, all 444 targets' glosses.json, 800 records
  with drafted_with: 8 null, 792 non-null, 503 match `^.+ \(.+\)$`, 289 (36%) do not (top:
  "claude-opus-5-5" 67, "Claude Opus 5.5" 49, "claude-fable-5-1" 41). DECISION: shape NOT enforced;
  the lead fixes the description instead.
- red: api/tests/test_mcpfix_wb2_gloss.py, 7 failed / 6 passed (wb2-5-red.txt).
- fix: `glosses.drafted_with_of` — whitespace-only (non-empty) drafted_with is `400 tooling-invalid`
  (`details.field: drafted_with`), dry run and real; null/"" still no model. A statement, witness or
  relation gloss with no `$`, `\(` or `\[` answers a `gloss-no-latex` warning in `warnings`, dry run
  and real (and so in the PR body's warnings note); built by the gate's rule `opn_gate.glosses.no_latex`
  so the codes test sees the emitter (catalog source "gate"); never a refusal, and the gate's own
  `modes.warnings` is NOT changed.
- restated (pinned the old behaviour): test_finding_drafted_with_spacing::test_only_whitespace_is_no_model
  -> ..._is_tooling_invalid; test_finding_gloss_dry_run and test_finding_gloss_warnings' "no warnings"
  cases now send a text with LaTeX.
- green: 13/13 new; 85 in the gloss/codes suites; the earlier 1350-test sweep over every gloss/codes
  test had exactly these 5 failures before the restatements.

## Item 1 — get_submission freshness (with the shared store pieces items 2 and 3 use)
- red: api/tests/test_mcpfix_wb2_freshness.py, 6 failed / 4 passed on both stores (wb2-1-red.txt);
  the backwards test was then restated (instance b reads only once the shared snapshot is past the
  window) and re-run red against the pre-fix code (appended to wb2-1-red.txt).
- fix: every fresh live read is written through (`pending.remember_pull`) to the store's ephemeral
  `pullstate#<n>` (TTL 1 h). A process with a copy of its own adopts the stored snapshot when it is
  strictly newer (`newest_snapshot`), so read_at never moves backwards; a process with no copy reads
  the host (newer than anything stored), which kept every existing cache test's meaning. The block
  carries `age_s`; `stale` is also true once age_s > pull_max_stale_s (pull_request_error unchanged).
  `pending.forget_pull` drops both copies (glosses' amend, racers' conversion); a withdrawal writes the
  closed state through (`remember_pull`).
- restated: test_finding_host_budget (served stale block now carries age_s: 300).
- NEEDS ADAPTER OWNER: api/opn_api/mcp/schemas/get_submission/v1.json `$defs.pull_request` is closed;
  add `"age_s": {"type": ["integer", "null"]}` (not required: a closed record's stored final_state has
  none). Until then 11 MCP tests fail "unschematic result" (listed in the report); with that one line
  added locally all 11 pass (checked, then reverted).

## Item 2 — merged, not yet rendered
- red: api/tests/test_mcpfix_wb2_pending_render.py, 4 failed (wb2-2-red.txt).
- fix: store `note_merged` / `recently_merged` / `forget_merged` (one string set
  `submissions#recentmerges`, `<pr>@<expires>`; both stores); `_reconcile` notes every record it closes
  as merged (6 h). `pending.awaits_render(ctx, sub)`: waiting_on_products' rule for its kinds, else the
  merge commit is not the target graph.json's rendered_from nor an ancestor of it (is_ancestor, kept per
  pair in new `Context.render_ancestry`; host failure or budget hold = nothing pending, C7). A merge the
  products carry is forgotten from the index. GET /frontier.json: entries whose node has a merged
  proof/counterexample/vacuity/reduction/partial awaiting render get `claimable: false`, and a top-level
  `pending_render: {node_id: {pr, kind, merged_at}}` is added AFTER frontier/v8 validation, and only
  when non-empty (frontier/v8 is closed at both levels; with nothing pending the document is still the
  committed one with claims, F05-AC15). `frontier.pending_words(ctx, target_id)` returns the
  `words:<target>:<subject>` keys of merged-unrendered glosses/explainers for the adapter.
- green: 8/8 (incl. both-store parity for the index); 447 in the frontier suites.

## Item 3 — annex hold
- red: api/tests/test_mcpfix_wb2_annex_hold.py, 3 failed / 1 passed (wb2-3-red.txt).
- fix: `precheck.WORDS_DIRS` gains `annex`; the one hold left is `check_cited_annex` for a bundle citing
  an annex main has and the products commit lacks: `precheck.annex_awaits_render` names the merge
  (`details.pr_number`, `details.merged_at` from the service's record, found in the recent merges or by
  reconciling an open annex record on the node; else null and "a merge on main") and passes merged_at,
  so retry_after_s = max(60, min(600, 840 - seconds since merge)).
- restated: test_finding_precheck_words_window's parametrized "annex holds a plan" case removed.
- note: the brief's "retry_after_s below 300 when the merge is recent" is backwards under the F06-T20
  formula (a recent merge has most of the median left, up to 600 s); the test uses a merge 10 min old
  (240 s) and asserts the formula's value.
