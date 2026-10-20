# F08-T43 / F10-T50 — running notes (agent, worktree `opn-lit-gate`, branch `lit-gate`)

Base: 8f33c2d0 (the lead's contract: literature/v2, graph/v13, frontier/v7, context/v9, v3.45).

## Orientation (read first)

- `modes.check_literature_record` today: schema → node → unsigned-with-`confirms` refused →
  `literature.signature_problem` → `confirms` must be a file on the node → signer-opener. Nothing
  reads `disputes`, so an unsigned record disputing, a signed one carrying both, and a dispute of
  a missing / own / signed record all pass with `[]`. That is the honest red for every (a)–(d).
- `literature.derive` already publishes `disputes` when the latest counting confirmation names a
  proposal in `disputes` and confirms nothing; a `disputes` naming a non-proposal publishes null.
- `context._literature_inline` already inlines `summary[:2000]` and `references[:20]` through the
  `Reader` seam with a fixed fallback; the F10-T50 tests are pins of a behaviour the contract
  commit shipped, plus the parity and the cap cases that no test covered.
- `codes.CATALOG` is the registry the guide-names test reads: a new diagnostic code must be added
  there or the guide cannot name it.
- Size budget (§6, `context.MAX_BYTES` = 256 KiB): one inlined record is at most 2000 (summary)
  + 20 × (300 title + 500 url + 500 note + keys) ≈ 28 KB; two records ≈ 56 KB, well inside the
  256 KiB cap, and `fit` drops attempt records first. No cap change needed; the schema's own caps
  (2000 / 20 / 300 / 500 / 500) are the smallest that keep it inside, so `_literature_inline`
  applies exactly those.

## Decision: code for a record carrying both `confirms` and `disputes`

New code `literature-record-conflict`, not `record-invalid`. `record-invalid` is the schema-shape
code and `literature/v2` cannot express the exclusivity (both fields are independent `oneOf`s,
no `allOf`/`dependentSchemas`), so a `record-invalid` here would be the one `record-invalid` with
no schema path behind it; an agent reading `GET /errors.json` gets a remedy specific to the act
("name one or the other"). Added to `codes.CATALOG` and to the guide's sentence of refusals.

## Log

### F08-T43

1. Wrote ten tests in `gate/tests/test_literature.py` (harness: `document()` stays v1 by default so
   every older test is a v1 regression; `disputes=` or `schema="literature/v2"` makes a v2 record).
2. First red was NOT on the defect: all seven failed `record-invalid`, because
   `paths.SCHEMAS_FOR_ROLE["literature"]` still pinned `("literature/v1",)` and the gate refused
   every v2 record at the schema step. Added v2 to the accepted set (a seam at today's behaviour,
   no rule) and re-ran: five honest reds, each `assert [] == [<code>]` — the gate accepted what it
   must refuse (`task-43-red.txt`). The products-side tests (dispute published on row / entry /
   bundle, proposed-again, no status change, non-steward, v1 regression) were green already: the
   contract commit shipped `derive`.
3. Rule: `check_literature_record` refuses an unsigned record carrying `disputes`
   (`literature-signature`); the signed-record naming checks moved into
   `_literature_named_problems` (ruff's branch cap): both set → `literature-record-conflict`
   (new catalog entry); `disputes` of a missing file / the record itself / a signed record →
   `literature-record-unknown` (message says which; `_not_a_proposal`). Signature and signer
   problems come first, so a stranger's dispute is `literature-signer-unlisted` as before.
4. Guide: two additions to "Literature records" (the dispute act and its refusals; the inlined
   summary and references in `CONTEXT.json`/`get_node`). `test_graph_copy_is_identical` is red
   as expected (the graph copy is the lead's at the re-pin); every other guide test is green.
5. `palomar_feed.propose` validates as `literature/v2` with `disputes: None` (its test is in the
   green run). Green run: 197 passed (`task-43-green.txt`); lint and mypy --strict clean.

### F10-T50

1. `gate/tests/test_finding_context_literature_inline.py` (unique name): the record's words reach
   `literature_proposed` and `literature` (confirming a proposal inlines the proposal's words, a
   steward stating the status inlines her own); a missing record and four unreadable shapes
   (not UTF-8, not YAML, not a literature record, empty summary) yield the fallback and the
   bundle validates as `context/v9`; the bundle is byte-identical through `DiskReader` and a
   `BytesReader` serving a snapshot of the same tree (F10-Q7), with a dispute on the node; an
   oversize record served by the reader is cut to 2000 / 20 / 300; two records at the caps are
   under a quarter of `MAX_BYTES`.
2. The tests name seams that did not exist (`SUMMARY_MAX_CHARS`, `REFERENCES_MAX`,
   `TITLE_MAX_CHARS`, `UNREADABLE_SUMMARY`, `UNREADABLE_REFERENCE`); a red on a missing name is
   not red, so the constants went into `context.py` at today's literal values and
   `_literature_inline` reads them. First run: 11 passed — the behaviour shipped with the
   contract (`task-50-first-run.txt`), so these are pins. To show they bite, two in-memory mutants
   (`task-50-mutants.txt`, a `-p` plugin from the scratchpad, nothing on disk changed): A (no
   caps, no fallback) fails the five fallback tests and the cap test; B (inline through
   `DiskReader` only, the F10-Q7 hazard) fails the parity test and the cap test. The three
   words-reach-the-bundle pins survive both, as they should: both mutants still inline the real
   words through the gate's own reader.
3. Size budget: measured, not estimated — two records at every cap canonicalise to under
   `MAX_BYTES // 4` (the test asserts it), so no cap below the schema's is needed and the §6
   budget is untouched.
4. Green run: 106 passed over the context, literature and products files
   (`task-50-green.txt`); lint and mypy --strict clean.

### F08-T43, coordinator's addition (the path rule)

The service agent's finding — `paths.SCHEMAS_FOR_ROLE["literature"]` pinned to v1 — is the seam
the first red hit (log item 2) and v2 was added there in b1c02ff4. Added on the coordinator's
word: an explicit end-to-end test, a v2 proposal classified and checked with no diagnostic and a
v2 dispute of it likewise (`test_a_v2_proposal_and_a_v2_dispute_pass_the_path_rule_and_the_check`),
shown red under a mutant plugin that puts the rule back to `("literature/v1",)`
(`record-invalid`, `task-43-v2-path-rule.txt`) and green as committed. Grep of the gate for
`literature/v1`: no remaining code constant beside the deliberate pair in `literature.SCHEMAS`
and `paths.SCHEMAS_FOR_ROLE`; the docstrings and the `--propose` help that still said v1
(`palomar_feed`, `cli`, `literature`, the feed test, the guide's directory sentence) now say
v2 with v1 readable. The api's own `literature/v1` constants are the api agent's
(`api/opn_api/literature.py:42`), untouched. Full fast tier before this addition: 6484 passed,
13 skipped (playwright absent), `graph_copy_is_identical` deselected
(`task-43-full-fast-tier.txt`).

## Proposed ledger lines (for the lead; nothing under engineering/specs/ was edited)

- **F08-T43** ✓ (gate) — a dispute is a signed act: `check_literature_record` refuses an unsigned
  record carrying `disputes` (`literature-signature`), a signed record with both `confirms` and
  `disputes` (`literature-record-conflict`, new catalog code), and a `disputes` naming anything
  but an unsigned proposal on the node — missing, itself, or signed (`literature-record-unknown`);
  `paths.SCHEMAS_FOR_ROLE` accepts `literature/v2`; the products publish the signer's reading with
  the rejected proposal beside it and cover it; status, claimable and needs untouched (D-25); v1
  records derive as before; guide updated. Tests: `gate/tests/test_literature.py` (+11).
  Verify: `uv run --frozen pytest gate/tests/test_literature.py gate/tests/test_palomar_feed.py
  gate/tests/test_catalog.py gate/tests/test_error_codes.py
  gate/tests/test_finding_guide_names_exist.py -q`. Evidence: `engineering/evidence/F08/task-43-*.txt`.
  Commits b1c02ff4, 04671899.
- **F10-T50** ✓ (bundle) — `context/v9`'s inlined `summary` and `references` pinned: the record's
  words for `literature_proposed` and `literature`, byte-identical through `DiskReader` and a
  host-shaped reader (F10-Q7), the fixed fallback for a missing or unreadable record (bundle still
  validates), the schema's caps as `context.SUMMARY_MAX_CHARS` / `REFERENCES_MAX` /
  `TITLE_MAX_CHARS`, two records at the caps under a quarter of the §6 budget (budget unchanged).
  Tests: `gate/tests/test_finding_context_literature_inline.py` (11). Verify: `uv run --frozen
  pytest gate/tests/test_finding_context_literature_inline.py -q`. Evidence:
  `engineering/evidence/F10/task-50-*.txt`. Commit ba220974.

Proposed Q entry (F08): **Q — `literature-record-conflict` rather than `record-invalid`** for a
signed record naming both `confirms` and `disputes`: the schema cannot express the exclusivity
(two independent `oneOf`s, no `dependentSchemas`), so the refusal is a gate rule with its own
catalog remedy, not a schema-shape error.

Not done, by rule: the graph's `AGENTS.md` copy (`test_graph_copy_is_identical` red; the lead's at
the re-pin); the api's `literature/v1` constant (`api/opn_api/literature.py:42`, the api agent's).
