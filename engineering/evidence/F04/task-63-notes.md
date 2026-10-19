# F04-T63 — literature marks, disputes, confirm/dispute on the node page (running notes)

Worktree `/Users/mikehiggins/Desktop/repos/opn-lit-site`, branch `lit-site`, from `8f33c2d0`
(the lead's contract commit: `graph/v13`, `frontier/v7`, decisions v3.45).

## Read first (2026-10-19)

- Constitution C1–C9; conventions §2, §3, §6. F04-Q16 (the key sits inside the drawing and
  names every state); the 2026-09-18 and 2026-10-04 log entries (measure labels, hover after
  scroll); 2026-09-24 (guard the renderer's outputs, not its inputs).
- The site has one theme (`site.css` is dark-only; "both themes" in older notes means the dark
  surface and the dark background). The three literature colours are chosen to read on both a
  dark and a white ground anyway.
- Where literature is rendered today: `render.py` `literature_block`, `literature_entry`,
  `literature_waiting` (the `/me/` rows), `known_parts` (the one-line "Literature:" in the
  panel and on the node page); `model.py` `LiteratureView`, `_literature_for`; `me.js`
  `confirmButton`. The drawing is `one_view._dag_svg` / `_pill_markup` on the problem page
  (F30) and `dag.svg` for the older single-view renderer (still used by tests and `dag`'s own
  callers); the key is `render.graph_legend`.
- The live graph at `/Users/mikehiggins/Desktop/repos/opn-lit-graph` (`00f4bc884`, read-only):
  `graph/v12` still (the re-pin to the contract has not happened), 65 nodes on erdos-1094, 12
  with `literature_proposed` (11 `known`, 1 `open` on the open core `--h2`), none confirmed.
  `erdos-1094--h2--h1--h1` carries a `known` proposal by `t1009-c`;
  `erdos-1094--h2--h2--h3--h1--h1` carries no record.
- The service route (`api/opn_api/literature.py` `post_confirm`): body `{node_id, record,
  status, references, summary}`; the other agent adds `disputes` (exclusive with `record`).

## Plan

Part 1 (drawing): `dag.LitMark` + `dag.literature_mark(mark, width)`, a 7px square in the
pill's top-right corner *inside* the rect (the outline tab sits outside, top-right; the halo is
at the right middle; the text ends at `w-18`), hollow and dashed while proposed, filled once
confirmed, coloured by status through three new tokens. The layout is untouched (the mark is
markup only). The key gets one item per (status, phase) the drawing shows, each a hover card
carrying `literature_words()`; a guard test iterates every class the mark can emit.

Part 2 (node page): `LiteratureView.disputes`; the dispute sentence in `literature_block`; a
hidden `.lit-act` row on the node page with the proposal's data, which `literature.js` shows to
a steward of the target or a curator with Confirm and Dispute; `me.js` reuses the same
`confirmButton` through `window.OPN.literature`.

Part 3 (evidence): render the live graph read-only, shoot and measure with Playwright.

## Log

### Part 1 — the mark (2026-10-19)

- Red first: `task-63-part1-red.txt`. With the renderer untouched, the page tests failed on the
  defect (no `lit-mark` on any pill, no title, an empty literature key, no `--lit-*` token); the
  seam tests failed on missing names only after the drawing seam (`dag.LitMark`,
  `dag.literature_mark`, the `literature` argument of `dag.svg`, `one_view._pill_markup`,
  `_dag_svg`, `drawing`) had gone in, so those four are not counted as red.
- Green: `site/tests/test_finding_literature_marks.py` 14 passed; the site tier 780 passed,
  12 skipped (Playwright), no golden moved (the row template's `$lit` and the key's items are
  empty for every node without a record).
- Geometry: a 7px square at `translate(w-16, 4)` — right of the label's end (`w-18`), above the
  halo (`y` 15–21), left of the outline tab (`x` from `w-8`, found and moved after the first
  live shot showed five erdos-1094 nodes carry both a proposal and an annex). The layout never
  reads it (`dag.layout` equal with and without the fields; the SVG with the marks stripped is
  byte-identical to the SVG without them).
- Colours: `--lit-open #4fa3e3` (blue), `--lit-known #e8913a` (orange), `--lit-elementary
  #4dbd7a` (green). None is a proof-status colour (accent purples, warn amber, bad red, select
  amber, the greys); the test asserts the three tokens are apart from every proof colour token.
  Hollow and dashed while proposed, filled when confirmed: the phase never rests on colour.
  The three statuses differ by colour alone at 7px (a letter does not fit); the title and the
  key's words carry the status for anyone who cannot read the hue.
- The key: one item per (status, phase) the drawing shows — `open, proposed`,
  `known, proposed` on the live erdos-1094 — each a hover card with `literature_words()`, the
  phase's meaning and D-25's "never about difficulty" sentence. The guard test iterates every
  class `dag.literature_mark` can emit (every status in `LITERATURE_WORDS` × proposed/confirmed)
  and holds the key to each.
- The listing row carries the badge inside its `.state` cell (the row is a fixed-column grid, so
  the badge could not be its own cell); at 390 the row hides `.state` and the badge with it, as
  it hides the state word. The node page's head carries it after the status mark.

### Part 2 — disputes and the node-page controls

- Red first: `task-63-part2-red.txt`: the block showed no dispute sentence, the panel none, the
  node page no slot, `literature.js` did not exist; two model tests failed on the missing
  `disputes` attribute (names, not red).
- `model.DisputedProposal` + `LiteratureView.disputes` (read from `graph/v13`'s
  `literature.disputes`; absent or null before). The block's sentence:
  "`mike` disputed `t1009-b`'s proposal (Open problem: no proof is known; record) and reads the
  statement as **Known: …**", placed after the fact line and before the signer's references and
  summary (which stays the demarcated untrusted block, rendered from the signer's own record).
  The rejected record joins the page's rendered-files list (R2).
- `static/literature.js` (new): `OPN.literature.confirmButton` / `disputeButton`; on a node
  page it waits on `OPN.session` and shows the hidden `.lit-act[data-target]` slot only to a
  signed-in curator or a steward of that target. `me.js` now reaches Confirm through
  `OPN.literature.confirmButton` (the T38 test restated to that rule, not deleted). Dispute
  posts `{node_id, disputes, status, references: [{title, url|null, note: null}], summary}`;
  Confirm posts exactly what `/me/` posted before.
- `render.lit_row` is the one function that writes the row on `/me/` and on the node page
  (the test asserts the two rows are byte-identical).
- The browser tests (`test_finding_literature_dispute.py`, Playwright, against a fake service
  in process) drove a steward session: Confirm and Dispute drawn, the dispute form filled and
  posted (body asserted), Confirm's body asserted equal to the proposal's fields, a signed-out
  reader and a steward of another target see no control, a curator sees both; shots
  `task-63-node-act-*.png`. So the signed-in state *was* captured, through the fake service,
  not the live one.

### Part 3 — the live render

- `PYTHONPATH=gate:site OPN_SITE_API_URL=https://api.example.test uv run --frozen python -m
  opn_site.cli render --graph /Users/mikehiggins/Desktop/repos/opn-lit-graph --commit
  00f4bc884917ca439772c6b72186ba5438c3f715 --out <scratch>` → 351 pages; the graph checkout
  stayed clean (`git status` empty). `task-63-shoot.py` served it and measured
  (`task-63-measure.json`): 12 marks on erdos-1094 (11 `known, proposed`, 1 `open, proposed`
  on the open core `--h2`), every mark inside its pill's rect, clear of its label and clear of
  the outline tab (checked against the tab's own bbox), key items inside the key's box at 1440
  and 390, `scrollWidth == innerWidth` on all three pages at 390, the signed-out node page with
  the slot hidden and zero controls in `main`, the head badge's title on `--h2--h1--h1` and no
  badge, block or slot on `--h2--h2--h3--h1--h1`.
- Looked at: `task-63-problem-graph-1440.png` (marks read as small orange/blue squares at the
  pills' top right; the one blue one is the open core), `task-63-problem-key-hover-1440.png`
  (the key's two new items, the hovered card with the words), the head and block shots, the 390
  key (wraps to five rows inside the card) and graph (the drawing scrolls inside `.dag-scroll`
  as before; the page itself does not). Nothing in them looked wrong after the tab move; the
  first key-hover shot was an element screenshot that lost the hover (the 2026-10-04 lesson,
  paid again) and was retaken as a viewport clip.

## Proposed ledger line (F04 §10 Tasks:, not written by this agent)

T63 ✓ 2026-10-19 (Q53, D-25 v3.45; worktree agent `lit-site`; red first 10 failed on the mark
and key with the drawing seam in place, then 8 on the dispute sentence, slot and script; green
`test_finding_literature_marks.py` 14 and `test_finding_literature_dispute.py` 10 + 2 in a
browser; site tier counts in the notes; the live graph `00f4bc884` rendered read-only: 12 marks,
all inside their pills and clear of labels and outline tabs, key items in the key at 1440 and
390, no sideways scroll; the steward's Confirm and Dispute driven against a fake service;
`engineering/evidence/F04/task-63-*`; on the site at the next deploy, the dispute sentence once
the re-pin publishes `graph/v13`).

## Proposed Q entry (F04-Q53)

**The literature status is a mark on the pill, never a state of it (T63, 2026-10-19; D-25
v3.45).** The owner read erdos-1094 against the literature and could not tell on the drawing
which statements carried a `known` proposal. A node's literature status is drawn as a 7px
square inside the pill's top-right corner — inside, because the outline tab already hangs
outside and a mark must be measured against its pill — coloured by status through three tokens
that are none of the proof colours (`--lit-open` blue, `--lit-known` orange, `--lit-elementary`
green), hollow and dashed while a contributor's proposal awaits a steward or curator and filled
once one has signed, with the status, who, and whether it awaits in its own title. The pill's
status ring, fill and class are untouched: a `known` statement is still open work, since
nothing is in Lean, so it is never drawn as done or muted. The key names each (status, phase)
the drawing shows with `literature_words()` in its card, and a guard iterates every class the
mark can emit (Q16's rule, guarded on outputs). The mark is markup only: `dag.layout` is equal
with and without the fields and the selector, the sets table and the layouts are byte-identical,
which is D-25's "feeds nothing" as a test. The same square is an inline badge on the listing row
and the node page's head. The node page states a dispute as a sentence after the fact line and
carries the awaiting proposal as a hidden row that `literature.js` shows, with Confirm and
Dispute, only to a signed-in steward of the target or a curator; `/me/` draws its Confirm through
the same function. Reversal: `dag.literature_mark`, `render.literature_key`, `lit_badge`,
`literature_act`, `static/literature.js`; the fields stay in the model.

## Not done / for the lead

- `engineering/specs/` untouched (ledger line and Q text above).
- Nothing needed from `gate/` or `api/`; the dispute post assumes the service accepts
  `disputes` exclusive with `record` (the other agent's change) — the site only sends it.
- The live graph still publishes `graph/v12`, so no dispute sentence can show live until the
  re-pin; the marks show at the next site deploy from the current products.
- The three statuses differ by colour alone at 7px; if that matters to a reader, a distinct
  shape per status is the next step (the title and key already carry the words).

## Final run (2026-10-19)

- `uv run --frozen pytest site/tests -m "not lean and not docker and not network and not
  harness" -q`: **790 passed, 14 skipped** (the skips are Playwright; the two new browser tests
  ran green under `--with playwright`, shots in the evidence). `make lint` exit 0.
  `uv run --frozen mypy --strict site`: no issues in 113 files. `task-63.txt`.
