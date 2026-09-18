# Handoff: openproofnetwork.org redesign (option 3a)

## Overview

A redesign of the public site rendered by `site/opn_site/` in `thisisanameforsure/open_proof_network`. Goals: a home page a mathematician or a compute contributor understands in one screen; plain-word vocabulary on the site (the protocol, API and repo keep theirs); hover definitions for every non-obvious term backed by one Glossary; the Targets and Frontier pages merged into one Problems page grouped by problem; hashes, origins and D-numbers moved out of the main views into detail panels and Docs; a new About page holding the long argument that currently opens the home page.

Design direction chosen by the owner: **option 3a** in the design file (the section at the top, badged `3a`, whose nav reads Home · Problems · Contributors · Docs · About). Section `2a` below it is the previous iteration and is included only as a fallback for the pages 3a does not redraw (Contributors, the rest of Docs). Section `1a` is an older light-theme direction and should be ignored.

## About the design files

`design/Open Proof Network.dc.html` is a **design reference built in HTML**, not production code. It renders a canvas of desktop (1440) and mobile (390) artboards. Open it in a browser (it needs `support.js` and `nocturne.css` beside it, and Inter from Google Fonts; without network it falls back to system-ui). Hover cards, the statement-graph selection and the "Record details" toggle are live in it.

The task is to **recreate these designs in the existing generator**: `string.Template` files under `site/opn_site/templates/`, HTML assembled in `site/opn_site/render.py`, one stylesheet `site/opn_site/static/site.css`, one optional same-origin script per page, no external resources (F04-R10), everything from the graph escaped (F04-R3), golden-file tests under `site/tests/golden/`. Do not port the design's React runtime, inline styles or the Nocturne bundle; translate the values into `site.css` variables and classes.

## Fidelity

**High-fidelity for layout, hierarchy, vocabulary and copy. Medium for colour.** Recreate spacing, type scale, grouping and interactions as specified. The palette below is the Nocturne dark theme used in the mock; if the owner decides to keep the current light `site.css` palette (`--paper`, `--ink`, `--proved`, `--ready`, `--blocked`), keep every structural decision and map the roles (see "Colour mapping"). Ask before changing which of the two palettes ships; the mock assumes dark.

## Constraints from the repo you must respect

- Every page is a view of committed graph files and links them at the rendered commit (F04-R2). The footer line stays; the mock moves it into a compact provenance bar (see Home).
- Nothing off-origin except `COPY_LINKS` and validated record URLs (F15-R11); the link checker in `site/opn_site/links.py` will fail the build otherwise.
- The whole Problems list must be in the HTML without JavaScript; the script only filters/hides (same rule as today's `frontier.js`).
- Hover cards must also work without a pointer: implement as `<details>`/`<summary>`-style or a focusable button with `aria-describedby`; on mobile the legend becomes an expandable panel (mock shows the collapsed control).
- `frontier.json`, `/targets/<id>/`, `/nodes/<t>/<n>/` and the API keep their names. Only the site's words and page set change. Keep `/targets/` and `/frontier/` as redirects to `/problems/` for existing links.
- Golden tests will need regenerating; `test_copy.py`, `test_finding_bench_claimable_words.py`, `test_finding_not_claimable_reasons.py` assert on specific words (see Vocabulary) and must be updated in the same change.

## Vocabulary (site words → protocol words)

Apply on every public page. Keep the right column in Docs, the API, `frontier.json` and the repo.

| On the site | Protocol / repo | Notes |
|---|---|---|
| Problem | target | Page `/problems/`; `NAV` entry "Problems" |
| Statement | node | "the problem's statement" = root node |
| open | ready (on the frontier) | statement status |
| blocked | blocked | unchanged |
| proved | proved | unchanged |
| Explained | digested / `proved_explained` | one of three stage marks |
| Written up | written-up | third stage mark |
| Steward | steward (D-32) | unchanged word, now prominent |
| Needs a steward | no steward → refuses claims | problem status |
| Curator | curator (D-6) | About/Docs only |
| statement unchecked | fidelity: mechanical-only | tag on a problem |
| statement checked | fidelity: hand-checked, unsigned | tag on a problem |
| statement signed | fidelity: non-author signature | tag on a problem (not in mock data) |
| Work on this / Work on a statement | claim (D-25) | button label |
| Attempt | attempt (D-13) | unchanged |
| Open statements | frontier | filter label on Problems |
| Record details | hash, origin, mathlib pin, files | toggle on statement panel |

Problem status words (replacing `STATUS_WORDS` on public pages): `open`, `proved`, `needs a steward`. A resolved target shows `proved` plus the three stage marks; the digestion state is expressed by which marks are filled, not by "resolved — undigested".

D-numbers (D-25, D-32 v3.17 …) are removed from Home, Problems, problem detail and About body copy. Keep them in Docs and in the Glossary's third column.

## Site map

| Path | Page | Status in this handoff |
|---|---|---|
| `/` | Home | redesigned (3a) |
| `/problems/` | Problems (Targets + Frontier merged) | redesigned (3a) |
| `/problems/<target_id>/` | Problem detail | redesigned (3a) |
| `/nodes/<target>/<node>/` | Statement record | not redrawn; keep current template, rename words, add breadcrumb `Problems / <target> / <node>` |
| `/contributors/` | Contributors | not redrawn; see 2a for styling reference, rename words |
| `/docs/` | Docs | keep content; add Glossary section at `/docs/#glossary`; move "Stewards" and "Propose a problem" prose intact |
| `/about/` | About | new page; receives the three long paragraphs currently in `home.html` `#lead`, plus the four rules |

`NAV` becomes: `("/", "Home"), ("/problems/", "Problems"), ("/contributors/", "Contributors"), ("/docs/", "Docs"), ("/about/", "About")`, plus one primary button at the right of the masthead: "Work on a statement" → `/problems/?filter=open`.

## Screens

Measurements are from the 1440 desktop artboards. Spacing uses an 8-step scale (see Design tokens); "s8" = `--space-8` etc. Mobile is 390 wide with s6 (≈17px) side padding.

### 1. Home (`screenshots/01-home-desktop.png`, `02-home-mobile.png`)

**Masthead**: full width, s4 vertical / s8 horizontal padding, 1px bottom rule (`--color-divider`). Brand: 8×8 accent square (radius 2) + "Open Proof Network" 500 weight. Nav links 14px, muted; current page in text colour. Right: primary button "Work on a statement" (outlined accent, see Buttons).

**Hero**: two-column grid `7fr 4fr`, column gap 3×s8 (≈67px), padding 3×s8 top, s8 sides, 2.5×s8 bottom.

- Left column: 
  - h1 60px / 1.05, weight 500, max-width 20ch: **"Open problems, proved in Lean, explained by people."**
  - Paragraph 18px / 1.6, `--color-neutral-300`, max-width 56ch: *"Anyone, person or program, may prove a **statement** here. Every problem has a named **steward**, a mathematician committed to understand and write up whatever is proved. A proof is not finished until they have."* The two bold words are defined terms (dotted underline, text colour, hover card).
  - Button row, gap s3: primary "Browse problems" → `/problems/`; secondary "Propose a problem" → proposal form URL (issue template); ghost "Why this exists →" → `/about/`.
- Right column: the counts card. Background `linear-gradient(160deg, --color-section, --color-section-glow)`, radius `--radius-md`, padding s8, column gap s6.
  - Big number 64px / 1, weight 500, tabular: `"{explained} / {proved}"` (from summed `digestion.proved_explained` / `digestion.proved`, exactly what `home()` computes today).
  - Label 15px `--color-accent-100`: "proved statements explained".
  - 13px `--color-accent-200`: "The number the network is judged by. A proof counts as explained once a person who can explain it without the tool that produced it has signed off."
  - 1px rule (accent-700) then a 3-column grid, each: number 28px + 12.5px label. Cells: `{targets} problems`, `{frontier entries} open statements`, `{distinct stewards} stewards`. Drop the other four counts from the home page (routes refuted, variants resolved, variants partial stay available on Problems/Docs if wanted).

**Open now** (padding 0 s8 2×s8): heading "Open now" 22px + ghost link "All {n} problems →" right-aligned. Then a list, one row per problem, grid `170px 1fr 150px 190px`, gap s6, s4 vertical padding, 1px bottom rule per row:
  1. target id, monospace 14px, `--color-accent-300`, links to the problem
  2. informal statement 15px / 1.45, `--color-neutral-200`
  3. "{n} open statement(s)" or "no open statements", 13px muted
  4. "Steward · {name}" (`--color-neutral-300`) or "Needs a steward" / "Steward wanted for write-up" (`--color-accent-300`)
  Show up to 5: unproved problems first, then a proved-but-unexplained one if any.

**Two cards** (grid 1fr 1fr, gap s6, padding 0 s8 2×s8), each `.card` with s6 padding, gap s3: kicker (12px uppercase, 0.08em tracking, muted) + h3 19px + 14px body + ghost link.
  - "Mathematicians" / **Propose a problem, or steward one** / "In ordinary mathematics, with references. No Lean needed. Unless you decline, you become its steward: your name goes on the problem, and the write-up is yours." / "How stewardship works →" → `/docs/#stewards`
  - "Bringing compute" / **Start with the tutorial statement** / "Prove `p ∧ q → q ∧ p`, run the checks locally, and you have a token. Then pick any open statement. Failed attempts are kept and count as contributions." / "Getting started · API →" → `/docs/#agents`

**Provenance bar** (replaces the footer paragraph on every page): surface background, s5 vertical / s8 horizontal padding, monospace 12px muted: `graph commit {short}` · `read-only · rebuilt on every merge` · right-aligned links `repository ↗ · frontier.json ↗ · claims.json ↗` (the last only when `api_url` is set, as `claims_note()` does today).

**Mobile**: single column; h1 34px; paragraph shortened to the first two sentences; two block buttons; counts band full-bleed with 48px number and 3-col mini grid; Open now rows stack id + steward on one line, informal beneath, min-height 44px.

### 2. Problems (`03-problems-desktop.png`, `04-problems-mobile.png`)

Replaces `/targets/` and `/frontier/`.

**Header**: h1 "Problems" 46px; lead 17px muted max 60ch: "Every problem on the record, with the statements its proof needs. Nothing is ranked; hover any term for what it means." Right side, stacked and right-aligned: segmented control `All {n}` · `Open statements {frontier count}` · `Proved {n}` · `Needs a steward`; beneath it a 280px search input "Search problems and statements". Filtering is client-side over the full list (same approach as `frontier.js`); the segmented options map to `?filter=all|open|proved|unstewarded`.

**Legend row** (padding 0 s8 s6): small uppercase "Legend" then chips, each with a dotted underline and `cursor: help`; the three status chips carry a 9px dot (filled accent = proved, accent outline = open, neutral-600 outline = blocked). Chips: open, blocked, proved, explained, written up, steward, statement unchecked, work on. Hovering/focusing opens a 300px card (surface bg, 1px divider border, radius-sm, shadow-md, 13px / 1.55 text) containing the definition and, in 11px monospace muted, `protocol: <protocol word>`. Definitions are the Glossary rows.

**Problem card** (`.card`, padding s6 s8, gap s5, one per target, sorted as `targets()` does today):

Top block, grid `1fr auto`, gap s8:
- Left, gap s3: 
  - row: target id monospace 17px accent-300 (link) · status tag (`.tag`, neutral: `open` / `proved` / `needs a steward`, hover card with the status definition) · outline tag `statement unchecked|checked|signed` (hover card with the fidelity definition).
  - informal statement 20px / 1.45, max 64ch.
  - source line 13px muted: e.g. "Imported from formal-conjectures (Apache-2.0) · erdosproblems.com/376" or "The network's own statement, no external source." (derive from `sources_block` data; one line, no licence prose).
- Right (min-width 260, right-aligned, gap s3):
  - three stage marks in a row, 12.5px: dot + "Proved", dot + "Explained", dot + "Written up"; filled accent dot and `--color-neutral-100` text when reached, neutral-600 outline dot and `--color-neutral-500` text when not. Derive: Proved = status resolved; Explained = digestion state ∈ {explained, written-up}; Written up = written-up.
  - steward line 13.5px: "Steward · {names}" or "Needs a steward" (accent-300) / "Steward wanted for write-up" for a proved problem with no steward.
  - ghost button "Open problem →" / "Open the graph →" → `/problems/<id>/`.

Statement list beneath, 1px top rule, one row per node, grid `16px 260px 1fr 150px 120px 160px`, gap s4, s3 vertical padding, 1px bottom rule, 13px:
  1. status dot (hover card: status definition)
  2. node id monospace `--color-neutral-200`, ellipsis
  3. role, muted: "the problem's statement" for the root, "definition" for origin `definition`, otherwise a short phrase from origin/relation (mock uses "n! ≠ 0, left open by the proof skeleton" for a skeleton-hole; use `origin` + `relation` words if no better source exists)
  4. state word: open / proved / blocked (with cause words from `CAUSE_WORDS` in the hover)
  5. attempts: "{n} attempt(s)" or "—" for definitions
  6. right-aligned action: "Work on this →" (accent-300) for open; "View proof →" (neutral-300) for proved; "Blocked" (neutral-500). Links go to `/nodes/<t>/<n>/`.

Footer note 13px muted under the list: "Showing {shown} of {total}. Hashes, origins and pins live on each statement's record page and in `frontier.json`, which lists exactly the open statements shown here."

Not-claimable reasons (`why_not_claimable`) move into the status tag's hover card for a `needs a steward` problem and into the statement page; they no longer render inline.

**Mobile**: header + 3-option segmented (All / Open / Proved) + a full-width secondary button "Legend: what the terms mean ▾" that expands the legend definitions inline. Cards stack: id + status tag, informal 16.5px, stage marks wrapped, steward line, then statement rows at min-height 44px with dot · id · action only.

### 3. Problem detail (`05-problem-detail-desktop.png`)

Header grid `1fr 380px`, gap 2×s8, padding 1.6×s8 s8 s8:
- Left: breadcrumb "Problems / {id}" 12.5px muted; h1 in monospace 34px `{id}` + status tag + outline `statement …` tag; informal 22px / 1.45 max 52ch; curator paraphrase / provenance 14px muted max 62ch; then the three stage marks (13px) as on the card.
- Right: `.card` "Steward" kicker; steward name(s) 17px or "None yet"; 13.5px muted explanation ("This problem is proved but not explained. It waits for a mathematician to commit to writing it up and to sign the explainer." for a proved+unstewarded problem; for an open one, the existing `stewards_section` cue shortened to two sentences); secondary button "Become its steward" → `/docs/#stewards`.

**Statements** section: h3 "Statements" + 14px muted "{n} statements. The problem's own statement is at the top; the rest are pieces its proof needs. Select one to see its record." Legend right: proved / open / blocked dots.

Grid `1fr 420px`, gap 2×s8:
- Left: the existing `dag.svg` output, 820×380 box, surface bg, radius-md, shadow-sm. Nodes are pills (bg, 1px divider border, radius-md, dot + monospace id 13px); edges neutral-700 1.5px; caption 11.5px bottom-left "arrows point from a statement to what it depends on". Clicking a node selects it (client-side; without JS every pill is a link to `/nodes/…`).
- Right: `.card` "Selected statement": id monospace 18px; two-row grid `status` / `attempts`; 14px muted note (the status words / cause); Lean block (bg `--color-bg`, 1px divider, radius-sm, s4 padding, monospace 11.5px / 1.7, pre-wrap); dotted-underline toggle "Record details (hash, origin, files)" revealing a 12px monospace grid: hash · origin · mathlib · files (Statement.lean ↗ · attestation ↗); primary block button "Work on this statement" / "View the proof →" / "View definition ↗".

Everything below (Statement QA table, approach records, state-of-the-problem note, evidence, drift) stays as rendered today, under the Statements section, with the section headings rewritten in site vocabulary ("Does the Lean say the conjecture?" for Statement QA).

### 4. About (`06-about-desktop.png`) — new page

Grid `1fr 300px`, gap 3×s8, padding 2×s8 s8 2.5×s8. Body max-width 68ch.
- h1 44px "Why this exists" + the first long paragraph from `home.html` verbatim (17px / 1.7, neutral-300). The two off-origin links are in `COPY_LINKS`.
- h3 24px "What the network does about it" + the second paragraph verbatim except: "It becomes claimable only while" → "It accepts work only while"; "marked resolved and, in the same breath, undigested" → "marked proved and, in the same breath, unexplained". (16px / 1.7, neutral-200.)
- h3 "What machines bring, when people stay in the chain" + the third paragraph verbatim minus its first sentence, ending "The record is organised so that…".
- 1px top rule, then a 2×2 grid of the four rules (kicker 01–04, h4 18px, 14px muted):
  01 Listed only after a search · 02 Worked on only with a steward · 03 Statement checked by a non-author · 04 Proved, then explained (copy in the design file `steps3`).
- Right column: `.card` "The steward's commitment" with the commitment blockquote (monospace 12.5px, 1px accent-700 left rule) + "One signed record, your own key, merged by pull request. No deadline; step down the same way." + ghost "Propose or steward →"; beneath it an "On this page" list (13px, current item accent-300).

### 5. Glossary (`07-glossary.png`) — new Docs section

`/docs/#glossary`, a `.table` with columns "On the site" (20%) · "Meaning" · "In the protocol" (24%, monospace 12px muted). Fourteen rows: the Vocabulary table above plus the definitions in the design file's `G` object (`design/Open Proof Network.dc.html`, logic class). This table is the single source for every hover card; render both from one Python dict.

### Not redrawn

- **Statement record** (`/nodes/…`): keep `node.html`; rename headings (Proof, Attestation, Attempts, Explainer, Annex unchanged), breadcrumb to Problems, status words per Vocabulary.
- **Contributors**: keep the table; 2a in the design file shows the intended dark styling (monospace handle in accent-300, muted numeric columns, mobile cards with three big numbers).
- **Docs**: keep all content; the D-numbers stay here. 2a shows a three-column layout (260px sidebar · 72ch body · 240px "On this page") that is optional.

## Interactions & behaviour

- **Hover cards**: trigger on `mouseenter` / `focus`, close on `mouseleave` / `blur` / Escape. 8px below the trigger, left-aligned, 300px wide (280 on tags, 260 on dots), z-index above cards. Content: definition text; legend cards add the `protocol:` line. No animation needed; if any, 120ms opacity.
- **Legend on mobile**: a `<details>` whose summary is the full-width button; content is the definitions as a stacked list.
- **Problems filters**: segmented control and search filter cards and statement rows client-side; without JS the full list renders and the segmented options are plain links with `?filter=`. Update the "Showing x of y" note like `frontier.js` updates its note.
- **Statement graph**: click selects; selected pill gets a 6px accent dot with a 4px 28%-alpha accent halo. Keyboard: pills are links, Enter follows.
- **Record details** toggle: dotted-underline text, hover turns accent-300; reveals the hash/origin/mathlib/files grid.
- **Buttons**: hover tint from the accent ramp, `:focus-visible` 2px accent outline offset 2px. Never the browser default ring (the current `site.css` already does this with `--ready`).
- **Hit targets** on mobile ≥ 44px.

## State management

Static site, so state is per page in the browser only: active filter (`?filter=`), search text, selected statement id (`#node=<id>` in the hash so it survives reload), which hover card is open, record-details open/closed, legend open on mobile. Nothing persists server-side.

Data the templates need beyond today's: distinct steward count for the home page (`len({s["login"] for tv in targets for s in tv.stewards})`), per-target open-statement count (`node_counts["ready"]`), a one-line source string, and the three stage booleans.

## Design tokens (Nocturne dark, as in the mock)

Colours: bg `#161826` · surface `#232532` · text `#e9e9ed` · divider `rgba(233,233,237,0.16)` · accent `#9184d9` · accent-100 `#f5f4ff` · accent-200 `#e7e5fe` · accent-300 `#d2cefd` · accent-700 `#5d5294` · neutral-100 `#f3f5fe` · 200 `#e4e7f5` · 300 `#cfd3e5` · 400 `#b2b6ca` · 500 `#9397ab` · 600 `#75798c` · 700 `#595d6c` · 800 `#3f424d` · section `#262a60` · section-glow `#353b80` (used only for the counts card gradient).

Type: Inter (or the system stack `system-ui, sans-serif` to honour F04-R10's no-external-resources rule — do not load Google Fonts in production). Headings weight 500, never bolder. Monospace: `ui-monospace, "SF Mono", Menlo, Consolas, monospace`. Scale used: 60/46/44/34/28/26/24/22/20/19/18/17/16/15/14/13.5/13/12.5/12/11.5 px.

Spacing (`--space-*`, 0.7× density): 1 = 2.8px · 2 = 5.6 · 3 = 8.4 · 4 = 11.2 · 5 = 14 · 6 = 16.8 · 8 = 22.4. Radii: sm 4px · md 8px. Shadows: sm `0 0 0 1px #3f424d`; md `0 0 0 1px #595d6c, 0 6px 18px rgba(0,0,0,.55)`.

Components: `.card` = surface bg, radius-md, shadow-sm; `.tag` = 12px, 2px 8px padding, radius-sm, neutral-800 bg / neutral-200 text; `.tag-outline` = transparent with 1px border; `.btn-primary` = transparent with 1px accent border, accent text; `.btn-secondary` = 1px neutral-700 border; `.btn-ghost` = no border, accent-300 text; `.seg` = 1px divider border pill row, selected option accent text + inset 1px accent ring; `.input` = bg, 1px divider, radius-sm.

### Colour mapping if the light palette is kept

accent → `--proved` (#1f6f45) for filled marks and primary outlines; accent-300 (link-ish text) → `--ready`; neutral-300/400/500 → `--ink` at 80/65/50% or `--muted`; surface → `--well`; divider → `--rule`; section gradient → a flat `--well` band with a `--proved` top rule.

## Assets

None. The brand mark is an 8×8 CSS square. Status dots are CSS. The dependency graph is the existing `dag.svg` output.

## Files

- `design/Open Proof Network.dc.html` — the design canvas. Section `3a` (top) is the chosen direction; `2a` is the fallback reference; `1a` is obsolete. Definitions, mock data and status logic are in the `<script data-dc-script>` block at the bottom (`G`, `problems`, `steps3`, `glossary`).
- `design/nocturne.css` — the token sheet the mock reads (`:root` variables and `.card/.tag/.btn/.seg/.input/.table/.nav` classes).
- `design/support.js` — the mock's runtime; not needed for the implementation.
- `screenshots/01–07` — one PNG per artboard of 3a.

Repo files this touches: `site/opn_site/render.py` (`NAV`, `home()`, `targets()`→`problems()`, `frontier()` folded in, new `about()`, glossary dict), `site/opn_site/templates/*.html` (new `problems.html`, `problem-row.html`, `about.html`, edits to `base.html`, `home.html`, `target.html`, `node.html`, `docs.html`), `site/opn_site/static/site.css`, `site/opn_site/static/frontier.js` → `problems.js`, `site/tests/golden/**`, and the word-asserting tests listed above.
