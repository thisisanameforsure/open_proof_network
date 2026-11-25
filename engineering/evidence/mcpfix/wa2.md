# mcpfix WA2 — compact, paged reads

Branch `mcpfix-wa2`, cut from origin/main ae6c445c.

## Log

- 2026-11-25 — baseline: `pytest api/tests -k "mcp or frontier or error_catalog or routes"` 366 passed.
- Measured before any code (live /frontier.json and the local graph checkout, 2026-11-22):
  - live frontier/v8: 601 entries over 443 targets, mean entry 589 chars compact, max 982;
    erdos-1094 alone has 69 entries = 44,965 chars.
  - the error catalog: 526 codes; {code, meaning} alone is 72,325 chars, so a no-arg answer of
    "every code with its meaning" cannot fit 25,000 chars: it is paged too (default 100).
  - list_sufficient_sets on erdos-1094 finest: 46 sets (106,659 chars), routes 53,566, selector
    8,156; any: 569 sets (886,114), selector 117,374.
  - get_node spec-a70fcca4--h4--h1--h1--h1 (the tester's 91k node): CONTEXT.json's witness.text is
    42,913 chars and is byte-identical to files["Witness.lean"], so the Lean is served twice.
- targets-index/v11 has no `title`; a summary row names the target's `root` instead.
- Red runs (each saved as wa2-<item>-red.txt): item 1 7 red, item 2 5 red, item 8 1 red
  (get_review target-unknown, list_submissions answered, list_frontier/list_targets refused the
  argument), item 3 4 red, item 4 5 red, item 5 2 red (include [] 101,314 of 102,721 chars),
  item 6 2 red (review.yaml fetched for all 450 targets). Item 7 red run on origin/main code
  (detached worktree at ae6c445c, the new test files copied in): list_targets 805,631,
  list_frontier 386,475, get_node include [] 101,287, get_hosted_checkers 49,315,
  list_error_codes 136,281, list_words_needed 499,021 — sizes in wa2-7-sizes.txt.
- Item 7 widened the work past the eight items: get_hosted_checkers (53,521 chars live, one row
  per target) and list_words_needed (499,021 on the fixture) were over the budget, so both
  answer compactly by default too; list_open_pairs reads only reviewed targets as
  list_review_questions now does (it walked the same 445 review.yaml reads in series).
- get_node: the context's statement.text and witness.text are the same bytes as
  files["Statement.lean"]/["Witness.lean"]; the tester's 91k node carried a 43k witness twice.
  When include leaves any section out, the context's copy is set to null (only when byte-equal)
  and `omitted` names it.
- list_sufficient_sets on live-shaped data (graph checkout 2026-11-22 + live frontier) is still
  over 25k by default on the busiest targets: erdos-1094 finest 98,730 (46 sets; routes 52,872
  of it), erdos-849 28,024, erdos-257 30,323. The routes, not the sets, are the bulk. See the
  report: compact route rows or a smaller default limit is the owner's call.
- tools/list (legacy surface) measured 114,974 before, 121,661 after; pin moved to 122,000.
- Green: 36 new tests in api/tests/test_mcpfix_wa2_*.py; restated 22 tests across 13 files.
- 2026-11-25T14:20:33Z — api fast tier + gate/tests/test_error_codes.py: 2553 passed. ruff, ruff format, mypy api, mypy gate clean.
