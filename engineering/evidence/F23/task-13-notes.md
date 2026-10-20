# F23-T13 / F05-T31 / F09-T74 — running notes (branch `lit-service`, worktree `opn-lit-service`)

Base: 8f33c2d0 (the lead's contract: `literature/v2`, `graph/v13`, `frontier/v7`, `context/v9`; decisions v3.45).

## What was done

1. **F23-T13 (with F05-T31), commit 1ca0a0be.** `api/opn_api/literature.py`:
   - `SCHEMA = "literature/v2"`; new `SCHEMAS = ("literature/v1", "literature/v2")` for what a record *on the
     node* may declare — the live graph's proposals are v1 and must stay confirmable and disputable (D-34).
     Before this, `checked_record` compared the file's schema to `SCHEMA`, so bumping the constant alone would
     have refused every v1 proposal on the record; the parametrised happy-path test covers both versions.
   - `POST /literature` writes `disputes: None` (F05-T31; one constant serves both routes, so the bump is in
     this commit rather than its own).
   - `POST /literature/confirm`: `CONFIRM_FIELDS` gains `disputes`; `checked_named` refuses `record` and
     `disputes` together (400 `arguments-invalid`, message naming both, `field: disputes`); `checked_record`
     takes `field=` and, for `disputes`, also refuses a file whose `via` is set (400: only an unsigned
     proposal can be disputed). 404 `not-found` and "not a literature record" 400 are as for `record`. The
     written record carries `confirms`/`disputes` as a mirror pair, validates as v2, is signed by
     `stewards.sign_record` as before; same rate limit, same `may_confirm`. The pull request's title is
     `literature: <node> disputed by <login>`, its `what` is `literature dispute` (a new `APPEND_CHECKS`
     entry in `appends.py`), and `extra_body` names the disputed file. `kind` stays
     `literature-confirmation` (one watchable kind; the record is the same signed kind to the gate).
   - `me.js` posts `node_id, record, status, references, summary` unchanged: tested as the mirror case.
   - MCP `confirm_literature`: optional `disputes` (same pattern as `record`, one-line description), forwarded
     under its own name through `present`; description says "Confirm or dispute", names `literature/v2`;
     `propose_literature` says `literature/v2`. Required set unchanged. The products test's assertion moved
     to `literature/v2` with a comment.
   - The service's derived bundle (F10-Q7, from the service's side): a node whose `literature_proposed`
     names a record on the fake host serves `context/v9` with that record's summary and references inlined,
     equal to the gate's `DiskReader` build of the materialised tree. Green without any api change: the
     service already builds through `opn_gate.context.build` with `HostReader`.
   - Three older tests pinned `literature/v1` as the written version; restated to `literature.SCHEMA`.
2. **F09-T74, commit (see below).** `get_node` and `list_frontier` descriptions gained a clause each
   (`literature`/`literature_proposed` inline summary and references; a confirmed status may carry
   `disputes`). New `api/tests/test_finding_literature_mcp_words.py` (2 tests). The budget test's comment
   block records the measurement; the pin is unchanged.

## Measurements

- `tools/list` before (8f33c2d0): **111,005** compact characters (`engineering/evidence/F09/task-74-before.txt`).
- `tools/list` after T41 + T74: **111,561** (+556, 0.5%; budget pinned 112,000, unchanged)
  (`engineering/evidence/F09/task-74-after.txt`). Of the 556: `confirm_literature`'s input schema +168 and
  its description +96; `get_node` +129; `list_frontier` +163.

## Test counts

- Red (seam missing, mostly `unknown-field`): 21 failed, 1 passed — `task-13-red-seam-missing.txt`.
- Red (seam at today's behaviour: `disputes` accepted and ignored, MCP parameter forwarded): 18 failed,
  4 passed — the route opened a confirmation-shaped v1 record for a dispute and refused nothing —
  `task-13-red.txt`.
- Green: the new file 22 passed; the nine literature/MCP suites 122 passed (`task-13.txt`); the whole api
  fast tier 2,163 passed; F05 slice 28 passed (`F05/task-71.txt`); T74 slice 25 passed
  (`F09/task-74-after.txt`). `make lint` exit 0; `mypy --strict api` clean (262 files).

## Findings for the lead / the gate agent (nothing under `gate/` edited)

- **`gate/opn_gate/paths.py:412` lists `"literature": ("literature/v1",)`.** That is the gate's
  per-directory schema rule; unless the gate agent adds `literature/v2` there, every record this service
  now writes (proposals and signed records alike) is refused by the gate's path/schema check at the merge.
  This must land before the re-pin that deploys this service change, or with it.
- `gate/opn_gate/palomar_feed.py` (`watch_palomar --propose`) still writes `literature/v1` proposals
  (`TITLE_CAP`/`SUMMARY_CAP` comments name v1 too). Valid under D-34 while v1 stays accepted; worth moving
  to v2 (`disputes: null`) when the gate side is touched.
- Grep of `.github/workflows/`, `api/tools/`, `gate/tools/` for literature phrases: no deploy smoke or
  workflow greps a literature phrase or `literature/v1`; `api-deploy.yml`'s smoke is untouched by this
  change. `api/opn_api/routes.py:82` has a comment saying "`literature/v1`" (comment only, not changed).
- `test_mcp_auth.py`, `test_mcp_surface.py`, `test_mcp_equivalence.py` and `test_finding_unknown_fields.py`
  carry `confirm_literature`/`/literature/confirm` bodies without `disputes`; all still green (the field is
  optional), none needed a change.

## Proposed ledger lines (not written to `engineering/specs/`)

- F23 **T41** ✓ 2026-10-19 (D-25, D-32 v3.45; worktree agent; red first 21 failed on `unknown-field` with
  the seam missing, then 18 failed on the defect with `disputes` accepted and ignored; green 22 in
  `test_finding_literature_dispute_route.py`, 122 across the literature and MCP suites, api fast tier 2,163;
  `engineering/evidence/F23/task-13*.txt`) — `POST /literature/confirm` takes `disputes` beside `record`,
  exclusive (400 naming both), an unsigned proposal on the node only (404 `not-found`; 400 for a non-record
  or a signed file); the signed record is `literature/v2` with the signer's own reading; v1 proposals on the
  record stay confirmable and disputable; the pull request says it is a dispute; `me.js`'s five fields confirm
  unchanged.
- F05 **T71** ✓ 2026-10-19 (same commit; `engineering/evidence/F05/task-71.txt`, 28 passed) — `POST
  /literature` writes `literature/v2` (`disputes: null`); the MCP `propose_literature` and
  `confirm_literature` say v2.
- F09 **T74** ✓ 2026-10-19 (`engineering/evidence/F09/task-74-before.txt`, `-after.txt`) — `get_node` and
  `list_frontier` say the literature fields inline summary and references and may carry `disputes`;
  `confirm_literature` carries `disputes` and says confirm or dispute; `tools/list` 111,005 → 111,561
  (+0.5%), pin 112,000 unchanged.

Proposed Q entry (F23-Qnn): **A dispute is a signed record naming an unsigned proposal, never a signed one
(T41, D-25 v3.45).** `record` and `disputes` are exclusive on `POST /literature/confirm`; a signed reading
cannot be disputed by name because a later signed record supersedes it anyway (the products publish the
latest counting confirmation), so the route refuses it 400 and says so. The watchable kind stays
`literature-confirmation`. The service accepts a v1 proposal on the node for either act (D-34: v1 records
stay on the graph), and writes v2 only.

## Log

- Read constitution, conventions §2/§3/§4/§6, `literature.py`, the MCP writes/reads/bijection, the schemas.
- Measured `tools/list` before: 111,005.
- Wrote `test_finding_literature_dispute_route.py` (22 tests); first red 21 failed on `unknown-field`
  (seam missing); added the seam at today's behaviour (`disputes` in `CONFIRM_FIELDS`, ignored; MCP
  parameter declared and forwarded); honest red 18 failed on the defect.
- Implemented the routes; 7 older tests red on their `literature/v1` pin; restated to `literature.SCHEMA`.
- `make lint` exit 2 (F811 from importing fixtures by name, five E501); rebuilt the fixtures locally over
  `harness_over`/`make_tree`, wrapped lines; lint 0, mypy 0. One scripted replace aborted on a substring
  that matched twice (the 2026-09-09 lesson) — redone with the Edit tool.
- Full api fast tier 2,163 passed. Committed 1ca0a0be (T41 + F05-T31).
- Moved the T74 words test to its own file so each commit is green alone; measured after: 111,561.
