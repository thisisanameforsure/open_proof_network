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
