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
