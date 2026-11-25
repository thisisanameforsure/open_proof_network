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
