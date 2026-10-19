# F08-T54 / F10-T50 — running notes (agent, worktree `opn-lit-gate`, branch `lit-gate`)

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

### F08-T54

1. Wrote ten tests in `gate/tests/test_literature.py` (harness: `document()` stays v1 by default so
   every older test is a v1 regression; `disputes=` or `schema="literature/v2"` makes a v2 record).
2. First red was NOT on the defect: all seven failed `record-invalid`, because
   `paths.SCHEMAS_FOR_ROLE["literature"]` still pinned `("literature/v1",)` and the gate refused
   every v2 record at the schema step. Added v2 to the accepted set (a seam at today's behaviour,
   no rule) and re-ran: five honest reds, each `assert [] == [<code>]` — the gate accepted what it
   must refuse (`task-54-red.txt`). The products-side tests (dispute published on row / entry /
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
   green run). Green run: 197 passed (`task-54-green.txt`); lint and mypy --strict clean.
