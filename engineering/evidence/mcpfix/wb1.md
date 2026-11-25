# mcpfix WB1 — the fast check (checks.py): scopes, echo, positions, partial labels, lint catalog

Branch `mcpfix-wb1` from origin/main ae6c445c.

- 2026-11-25 — read rules, the testers' calls (t883 item 3, qa-eb L4/L12, t257 item 2, t257b item 3).
- Probed AXLE directly (POST https://axle.axiommath.ai/api/v1/check and /verify_proof, tiny
  programs): it strips the sent text's header (imports, blank lines, `--` comments before the
  first command) and puts `import Mathlib\n\n` in its place; the echo's `content` is that text,
  and every position is a line of the echo. So a position is mapped echo → sent (by the echo's
  length against the sent text's) → the caller's own line (by the composition's line origins).
- Fetched erdos-883's nine defs files and its Statement.lean read-only from the graph's raw host;
  committed as api/tests/fixtures/erdos-883-defs/ for the scope test.
- Item 1 (scopes): red 3 failed (wb1-1-red.txt: the composed text had no `end` lines; on the
  erdos-883 files `end SimpleGraph` never appeared before the caller's theorem). `scope_closers`
  reads each inlined module over `lean_mask` (comments and strings blanked), one line at a time,
  tracking `namespace`/`section` (named, anonymous, `noncomputable`, attributes and visibility
  before it)/`mutual`/`end`, and `forward` appends the closers after each module. Green 3 passed
  (wb1-1-green.txt); 655 passed over the 50 api test files that touch the check.
- Item 2 (echo): red 3 failed of 4 (wb1-2-red.txt: `content` in result; echo "yes" accepted;
  no `echo` in the MCP schema). `result` now drops AXLE's `content` unless `echo: true`
  (route field and check_lean input `echo`, boolean, 400 `echo-invalid` otherwise, catalogued).
  heartbeats_of reads its own measuring answer's echo, which is never returned, so it is
  untouched.
- Item 6 (description): red 1 failed (wb1-6-red.txt). check_lean's description rewritten inside
  its 1,000-character cap: positions are lines of your text; a skeleton aims for
  `result.okay: true` in check with only sorry-present (`okay` stays false, F13-Q31); verify
  reports sorry as failure. NOT as the brief worded it: the brief said a skeleton aims for
  `okay: true` in check, but gate_verdict makes check-mode `okay` false whenever the caller's
  text carries sorry (F13-T30, F13-Q31, guide line ~384, tests in
  test_finding_check_verdicts_gate.py). The description says what the code does.
  The tools/list budget went 114,974 -> 115,069 and was re-pinned 115,500 with the measurement.
- Green: 453 passed over every check and MCP test file plus test_error_codes (wb1-2-6-green.txt).
- Item 3 (positions): red 4 failed of 6 (wb1-3-red.txt; the three-line proof read `-:5:9`,
  exactly qa-eb's report, and the one-line exhibit `-:10:23`). `forward` records each line's
  `Origin` (caller line, inlined module + its line + the import line that pulled it in, or
  network text); `witness_composed`/`hazards_composed`/`exhibit_check_text` likewise.
  `remap_body` lines AXLE's echo up with the text sent (`echo_shift`: line-count difference,
  checked by the last line; no echo or no match = nothing mapped, which keeps every fake-body
  test as it was) and `relocate` rewrites each `-:L:C[-L:C]` in lean_messages and
  tool_messages (errors, warnings, infos). Inlined positions -> `-:<import line>:0` plus a
  `[position: line N of Defs.X as inlined ...]` note line; statement lines in witness mode ->
  `statement:L:C`; network text -> `network:L:C` plus a note. `echo: true` returns the raw
  positions beside the echo. Applied to POST /check and to the exhibit pre-flight
  (`exhibit-elaboration` details.errors, both defect claims and revision requests, which share
  `preflight_exhibit`). NOT applied: `witness-fails`, `statement-fails`,
  `relation-elaboration` details on the proposal pre-flights (they keep the checker's lines).
- Green: 6 passed; broad run 1175 passed, 1 failed (wb1-3-green-broad.txt): the failure is
  gate/tests/test_walkthrough.py::test_graph_copy_is_identical, the sibling graph checkout's
  AGENTS.md copy drifted (no AGENTS.md change on this branch; known stale-checkout case).
- Item 4 (partial labels): red 2 failed of 3 (wb1-4-red.txt: no partial-unlabelled finding).
  Where `sorry-present` fires, `labels.problems(content)` runs and any problems become ONE lint
  finding `{"code": "partial-unlabelled", "message": <the precheck refusal's words>, "missing":
  [Problem.as_dict(), ...]}` — the same `missing` list the precheck's 400 carries. It does not
  change `okay` (sorry-present already makes it false in check and verify). Two older tests in
  test_checks.py that pinned the lint list for a sorry text were restated to include it.
  Green 20 passed (wb1-4-green.txt).
- Item 5 (catalog): red 2 failed (wb1-5-red.txt: 9 lint codes uncatalogued; proof-empty's source
  became both). test_error_codes' walk now collects `{"code": <literal or if-expression>}` dict
  values in api/opn_api/checks.py (LINT_SOURCES), and `header-diverges` is one of the walk's
  known-present codes. Rows added (source api, step None): imports-differ,
  helper-declarations, header-diverges, signature-diverges, sorry-present, admit-present,
  sorry-reported, import-unknown-node, context-restated (and echo-invalid, item 2). Already
  catalogued and now also lint: proof-empty and helper-forbidden (source gate -> both, meaning
  mentions the lint), node-superseded (api), node-shelved (both), partial-unlabelled (both;
  remedy mentions the lint). The use-* lint codes come from the gate's own Diagnostics and were
  already rows. No golden carries the catalog (errors.json is rendered at request time; the
  site's Docs page does not list codes), so nothing was regenerated. Green 13 passed.
- Broad run after items 4 and 5 (wb1-4-5-broad.txt, 2217 tests over every check/MCP/catalog
  test, the gate tests that import opn_api, and site/tests): 3 failed, of which two were the
  test_checks pins restated above and the third the sibling-graph AGENTS.md copy
  (test_walkthrough::test_graph_copy_is_identical, unrelated, stale checkout).
