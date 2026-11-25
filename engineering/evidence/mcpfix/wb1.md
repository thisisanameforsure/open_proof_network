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
