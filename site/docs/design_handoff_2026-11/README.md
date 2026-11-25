# Open Proof Network — site redesign brief

For: Claude Code, working in the `network` repo (`open_proof_network`), which renders
openproofnetwork.org from `site/opn_site/`.
Last updated: 2026-11-25 (problem page: route selector, selection, tabs, speculative statements, phone layout).
From: a design review done on 2026-11-24 against the live site, the public graph repo
(`open_proof_network_graph`) and pequalnp.com as a reference.
Design canvas (screenshots of every current page, review notes, mockups):
https://claude.ai/artifact/6gTMQk3wBJBPUoBBD5Apgo

`screenshots/` holds each proposed page at 1440 and 390 wide. The folder `mockups/` next to
this file holds the same pages as HTML. They are
design-canvas files (`.dc.html`): ignore the `<x-dc>`, `<helmet>` and `<script type="text/x-dc">`
wrappers and read the markup inside as plain HTML with inline styles. Treat them as the visual
spec, not as code to copy: rebuild them in whatever the site's own templates and CSS are.

## Start here

Paste this into Claude Code at the repo root:

> Run /session-start. Then read `site/docs/design_handoff_2026-11/README.md` (this file) in full,
> and `review/REVIEW.md` beside it. Turn the brief into the next feature spec under
> `engineering/specs/features/`, following §0. Before building, ask Mike the open questions in §8.

## What is in this folder

| Path | What it is |
|---|---|
| `README.md` | This brief: rules, design direction, page specs, data change, bug list, order of work, open questions. |
| `tokens.css` | The design tokens as CSS custom properties, light and dark, contrast-checked. Paste into `site.css`. |
| `mockups/*.dc.html` | The proposed pages as HTML (inline styles). Read the markup inside `<x-dc>` as plain HTML. |
| `screenshots/*-desktop.png`, `*-phone.png` | Each mockup rendered at 1440 and 390 wide. |
| `mockups/New-Problem-InfoMap.dc.html` | Every item on today's problem page and where it goes — the acceptance checklist for §3.4. |
| `screenshots/New-Erdos257-list-unfolded-proof-desktop.png`, `New-Erdos257-route3-desktop.png` | Older renders of an interactive draft. Ignore them; use the `New-Erdos257-List/-Unfolded/-Route3` screenshots. |
| `source/e257v2.py.txt` | Older generator for the problem page; `e257v3.py.txt` + `proof_section.py.txt` + `select.py.txt` are current. |
| `review/REVIEW.md` | The review of the live site and of pequalnp.com that led here, page by page. |
| `review/current/` | Screenshots of the live site on 2026-11-24, before any change. |
| `review/reference/` | pequalnp.com screens referred to in the review. |
| `source/*.py.txt` | The scripts that generated the mockups (`common.py.txt` holds the tokens and the status, stage-mark and sidenote markup). Reference only, saved as `.txt` so `ruff` and `mypy` in `make verify` skip them; they are not part of the site. |

Nothing here is rendered by the site: `render.py` only reads `site/docs/*.md` at the top level
(F10-R9), not this subfolder.

Pages covered: Home, Problems, problem page, Contributors, Docs (home + one article), steward
sign-up, My problems, formalization review. Every mockup:

| Mockup | Shows |
|---|---|
| `New-Home` | Home (§3.0) |
| `New-Problems` | Problems list (§3.2) |
| `New-Erdos257` | Problem page, worked problem — default state: Routes in Tree view, Route 2 drawn, proved statements folded, the problem's own statement in the panel (§3.4) |
| `New-Erdos257-List` | Same page, Routes in List view |
| `New-Erdos257-Unfolded` | Same page, Route 2 with proved statements unfolded |
| `New-Erdos257-Route1` | Same page, Route 1 drawn (a proof route, with a borrowed lemma) |
| `New-Erdos257-Route3` | Same page, Route 3 drawn (a disproof route) |
| `New-Select-Side` | Selecting a statement, option A: panel beside the tree (§3.4.3) |
| `New-Select-Inline` | Selecting a statement, option B: record opens under the box (§3.4.3) |
| `New-Select-Every-Tab` | The five tabs for a selected statement (A = primes) |
| `New-Erdos257-Panel-Tabs` | The five tabs for the problem's own statement (nothing else selected) |
| `New-Phone-Select` | Problem page on a phone (390 wide): route as an outline, record opening under the tapped statement (§3.4.6) |
| `New-Phone-Every-Tab` | The five tabs for a selected statement at phone width (§3.4.6) |
| `New-Problem-abc` | Problem page, problem with no work yet (§3.4.5) |
| `New-Problem-InfoMap` | Where every item on today's problem page goes (acceptance checklist) |
| `New-Contributors` | Contributors (§3.1) |
| `New-Docs-Home`, `New-Docs-Article` | Docs landing and one article (§3.3) |
| `New-Steward-Signup`, `New-My-Problems`, `New-Review` | Steward pages (§3.5) |

All mockups are static: one artboard per state. On the site, switching states (route, view,
fold, tab, selection) is one same-origin script per page over HTML that already contains every
state, so each page reads fully without JavaScript. The design
canvas with everything side by side: https://claude.ai/artifact/6gTMQk3wBJBPUoBBD5Apgo
(Mike's account).

---

## 0. Before you start — this repo's rules come first

This brief is design input. The repo's own law wins wherever they differ
(`CLAUDE.md` → `engineering/CLAUDE.md`):

1. Run `/session-start`: constitution → current spec → task ledger.
2. **Spec first.** Turn this brief into a feature spec — copy
   `engineering/specs/features/F00-template.html` to the next free number (F32 is the latest
   on 2026-11-24, so probably F33), with EARS requirements, acceptance criteria that each name
   a test, and dependency-ordered tasks with verification commands. Add it to
   `engineering/specs/index.html`. Cite decisions by D-number; never restate one.
3. **Each task is done only when its verification command passed**, output captured under
   `engineering/evidence/FXX/`, plus screenshots at 1440 and 390 for visual work. Commit per
   task as `FXX-Tn: …`. `make verify` before every commit.
4. **The generator's constraints stay** (same as the September handoff in
   `site/docs/design_handoff_site_redesign/README.md`):
   - `string.Template` files in `site/opn_site/templates/`, HTML assembled in
     `site/opn_site/render.py`, one stylesheet `site/opn_site/static/site.css`, at most one
     same-origin script per page (`render.SCRIPTS` is the allowlist).
   - **No external resources (F04-R10, enforced by CSP and `links.py`).** No Google Fonts:
     self-host any new font under `static/` with a sha256 `MANIFEST.txt` the way KaTeX is
     vendored (F04-Q15), or use the fonts the site already serves.
   - Everything from the graph is escaped (F04-R3). Never write a hostname into a template
     or page — the API base comes from config.
   - Every page stays readable without JavaScript; scripts only filter, hide or reveal.
   - Golden tests under `site/tests/golden/` and the copy tests (`test_copy.py` and friends)
     change in the same commit as the page.
5. The vocabulary table in the September handoff (Problem/target, Statement/node, open/ready…)
   still applies to every public page.
6. Do not change the graph repo's data or schemas until §4 is agreed with Mike and goes
   through the architecture document's own process.

## 1. Goals, in priority order

1. **Contributors** credits people: stewards first, then the people who bring agents (agents
   are their tools), then the full ledger, collapsed. No ranking.
2. **Problems** becomes findable: search, filters, the problems with work on them first, the
   438 waiting ones paginated.
3. **Docs** becomes a set of short pages by reader, instead of one 73,700px page that inlines
   all of AGENTS.md.
4. Fix the site-wide bugs in §6.
5. Move the whole site to the new look (§2). Problem pages and the erdos-257 graph view come
   after the three pages above.

Keep: the voice and copy of About, the home page headline, the "Same machines. Different
rules." idea, and the statement graph's **"Ways to settle the problem"** route picker — Mike
likes it most. It becomes the main control of the problem page (§3.4.2), with the tabbed
selected-statement panel beside it (§3.4.3).

## 2. Design direction — "Journal" (agreed with Mike, 2026-11-24)

The site is a public scientific record: nothing is announced, failures are published, a proof
is done when a person has explained it, and a named mathematician answers for each problem.
So it should read like a **well-made mathematics journal that happens to be live** — not a
dashboard (the old dark look) and not a live show (pequalnp.com). This replaces both the
September "Nocturne" palette and the "Paper & Ink" draft in earlier mockups; Mike has agreed
to the change, so this is no longer an open question.

Principles:
1. **Serif for reading.** Prose and headings in a text serif that sits beside KaTeX; sans
   only for controls, labels and small UI text; mono only for Lean and ids.
2. **Colour only where it means something.** Text is ink. Links are ink and underlined.
   Blue means *proved* and nothing else; rust means *refuted / failed*. Open is an ink outline.
   Every state is also a shape (● ○ ⊘), so the site works in greyscale.
3. **One signature mark: proved → explained → written up.** Three small dots joined by a
   line, filled as each stage is reached (`stages()` in the mockups). Use it everywhere a
   problem appears — problem rows, problem pages, steward cards — so visitors learn the
   site's thesis from the interface.
4. **Provenance in the margin.** Hashes, D-numbers, attestations, merge commits, sources and
   admission dates go in sidenotes beside the claim they support (a right margin column on
   desktop; under the paragraph on a phone), not in badges, body copy or a footer dump. The
   footer keeps one collapsed "Source of this page".
5. **The graphs are the pictures.** No stock imagery or illustration. Statement drawings are
   styled as figures: hairlines, white ground, a numbered caption ("Figure 1. Route 2 …").
6. **Calm about activity, few numbers.** Dated logs ("Lately on the record"), no live counters,
   tickers or rows of big stats — Mike's call: start with as few stats as possible. A number
   appears only where it tells someone what to do (e.g. "8 questions wait for you").
7. **Hairlines over boxes.** Radius 4, 1px rules, numbered sections (§1, §2 …), generous
   margins, prose capped near 70 characters.
8. **Dark scheme follows the reader's system** (`prefers-color-scheme`), from the same tokens.

Tokens, as CSS custom properties in `site.css`:

| Token | Light | Use |
|---|---|---|
| `--paper` | `#FAF9F6` | page ground |
| `--surface` | `#FFFFFF` | figures, cards, tables |
| `--tint` | `#F1EFEA` | code blocks, tool chips, empty bar track |
| `--ink` | `#1B1B1A` | text, links, primary button |
| `--muted` | `#5C5A55` | secondary text (≥ 4.5:1 on paper) |
| `--rule` | `#E3E0D9` | hairlines, borders |
| `--rule-strong` | `#B9B5AC` | figure connectors, link underlines |
| `--proved` / `--proved-tint` | `#2A4D8F` / `#E8EDF6` | proved fill; focus ring |
| `--refuted` / `--refuted-tint` | `#A0461E` / `#F7EAE3` | refuted, warnings |

Derive the dark scheme from the same roles (paper ≈ `#161615`, ink ≈ `#ECEAE5`, proved ≈
`#8FB0F0`) and check every pair for 4.5:1.

Type: **Source Serif 4** (body 18px / 1.6, headings 400 weight: H1 52px, H2 30px, H3 21–24px),
**IBM Plex Sans** (nav, buttons, labels, captions, sidenotes: 13–15px), **IBM Plex Mono**
(Lean, statement and problem ids, code). All SIL OFL — vendor the woff2 files same-origin with
a sha256 `MANIFEST.txt` as KaTeX is (§0.4). The mockups load them from Google Fonts only
because the design canvas can.

Layout: content max-width 1160px, 24px side padding. Pages with provenance use a two-column
row: main column (flex 999 1 560px) + margin column (flex 1 1 200px, max 250px) that wraps
under the main column on a phone.

Header: serif wordmark · Problems · Contributors · Docs · About · "Sign in" (outlined) ·
"Work on a statement" (filled ink, as today). Active nav item: ink text with a 2px ink
underline.

## 3. Pages

### 3.0 Home (`mockups/New-Home.dc.html`)

1. Headline "A proof is finished when someone can explain it.", the existing lead paragraph,
   two buttons: "See a problem being worked" and "Propose a problem". No counters.
2. **§1 One problem, worked** — Figure 1: part of erdos-1094's statement graph drawn in the
   figure style, with a numbered caption; beside it the statement and "Open erdos-1094 →".
3. **§2 Same machines. Different rules.** — the six rules as a numbered list, the usual
   practice struck through above each rule.
4. **§3 Where you come in** — mathematicians, readers of Lean, bringing an agent.
5. **§4 Lately on the record** — the existing dated log.

### 3.1 Contributors (`mockups/New-Contributors.dc.html`)

Today: `contributors.html` is one `$ledger` placeholder filled by `render.py` →
`contributors()` (around line 5489), one `<h2>` + table per ledger identity.

Sections, in order:

1. **Header**: H1 "Contributors", the line "Everyone here did something the record can point
   to. Agents are tools; the person who runs them is credited. Nobody is ranked." No stat row.
2. **Stewards**: one card per steward — name, GitHub handle, the problems they steward
   (links), how and when they were admitted. Today: Michael Higgins (erdos-1094, erdos-257),
   riversupport (co-steward of erdos-257 since 2026-10-29, invited by the panel),
   WilliamVerreault (erdos-849). Read these from the same records the problem pages use —
   don't hard-code them. A last dashed card: "438 problems need a steward → Steward a problem".
3. **People who bring agents**: one card per *person* (a pseudonym), sorted by last activity.
   Card: avatar, pseudonym, real name if they gave one, badge "GitHub linked" or "Anonymous",
   one sentence of counts (proofs, partial proofs, statements, failed attempts kept) — not a
   grid of number boxes,
   tools used (framework + models from each entry's `automation` field, with counts),
   problems worked on, and a collapsed list of the agent runs credited to them. Filters:
   Everyone / GitHub / Anonymous, plus a "Show test runs" toggle that is off by default.
   Last card: "Your name here" → Quick start.
4. **The full ledger**: a `<details>` closed by default — search box, a table (date, run,
   what, statement, model) with paging, and a link to `ledger/` on GitHub. Revoked entries
   stay listed, marked "revoked".

Until §4 is done, step 3 can't group runs by person honestly. Ship it in two stages:
- **Stage A (no data change)**: show stewards; show one card per ledger identity but in a
  compact list, test identities hidden (see §4.3); the ledger collapsed. Already a big
  improvement on the current 38,500px page.
- **Stage B (after §4)**: group runs under their person, as in the mockup.

Normalise model names before counting: the ledger has free-text values such as
`claude-opus-5-5`, `Claude Opus 5.5 (claude-opus-5-5)`, `aristotle (Harmonic)` and
`Aristotle (Harmonic, leanprover/lean4:v4.28.0)`. Map each to a canonical id (prefer the
string in parentheses when present; lower-case; strip version suffixes into a separate field).

### 3.2 Problems (`mockups/New-Problems.dc.html`)

1. Header: title and one sentence, no stat row. Today's tabs read "All 445 · Open 602 · Proved
   3" — "Open" counts statements, the others count problems; drop them, and put each problem's
   open-statement count in its row.
2. A filter bar: search (id, number, words in the statement), Status (being worked on / open,
   not started / proved), Steward (has / needs), Sort (recent activity / most open / name), and
   area chips with counts. Every filter is a URL query parameter so a view can be linked
   (the existing `?filter=` links keep working). Extend `static/problems.js`: it filters the
   rows already in the HTML, reading `data-` attributes the renderer puts on each row.
3. **With work on the record**: one row per problem — id + status pill + area, a one-line
   statement, a progress bar (proved vs open statements, with a text label), steward or
   "Needs a steward" / "Calibration target", runs and last activity. Sorted by last activity.
4. **Waiting for a first steward**: a compact table (id, statement, area, "Steward this").
   The whole list must stay in the HTML (see §0.4); the script shows the first 50 and a
   "Show 50 more" button, and the filters hide rows. Without JS, all 438 rows show — fine,
   because a table row is ~50px against today's ~250px card.
5. "Know an open problem that isn't here? Propose it…".

On a phone each row stacks (id + status, statement, bar, steward) — the mockup's 12-column
row is the desktop layout only; do it with one media query in `site.css`.

Statements here are one line of plain text with inline maths. Render maths with KaTeX at
build time if the site already uses it (it does on problem pages); otherwise plain Unicode
as in the mockup.

### 3.3 Docs (`mockups/New-Docs-Home.dc.html`, `mockups/New-Docs-Article.dc.html`)

Today `docs.html` is one page: short sections, then the decisions document and AGENTS.md
copied in whole (F04-Q6). Split it into one URL per topic under `/docs/`, each with a left
sidebar; keep `/docs/` as the landing page and keep old `#anchors` working by redirecting
or linking from the landing page. Sidebar groups:

- **Start here**: Overview · Three ways in · How a problem is worked
- **Mathematicians**: Steward a problem · Propose a problem · Review a statement · Sign an explainer
- **Readers of Lean**: Write the words for a statement · Check a statement is faithful
- **Agent operators**: Quick start · Getting a token · Claim a statement · Precheck and submit ·
  Connect your harness (MCP) · AGENTS.md (full text, link)
- **Reference**: API routes · MCP tools · Error codes · Rate limits · Glossary
- **Protocol**: Architecture decisions · The Leiden Declaration · Rules (policy.json)

Rules:
- **AGENTS.md is not inlined** into any docs page. Serve it as a raw file and link it, with
  `llms.txt` and the MCP command (`claude mcp add --transport http open-proof-network
  <api base>/mcp`, the base filled from config — never a literal hostname).
- Human guides are short rewrites of the matching AGENTS.md sections: what it is, steps,
  one code sample per step, callouts for what can go wrong, previous/next links. See
  "Getting a token" in the mockup — about 350 words against about 1,100 in AGENTS.md §"Getting
  a token (D-19)". Check every fact against AGENTS.md; it is the source of truth.
- Reference pages can be generated from the same sources the API uses (route list, MCP tool
  table, error codes) so they don't drift.
- Decision codes (D-19, D-32 v3.17…) appear once, at the foot of a page ("Protocol: decision
  D-19"), not inside the prose.
- Search: a same-origin script over a JSON index of headings and text the build writes; the
  sidebar is the no-JS fallback. (If that's more than the first pass needs, ship without
  search and add it as a later task.)

### 3.4 Problem page

Mockups: `New-Erdos257` (+ `-List`, `-Unfolded`, `-Route1`, `-Route3`), `New-Select-Side`,
`New-Select-Inline`, `New-Select-Every-Tab`, `New-Erdos257-Panel-Tabs`, `New-Problem-abc`,
`New-Problem-InfoMap`. Data in all of them is erdos-257's and abc's real record
(`targets/<id>/graph.json` and the live pages, 2026-11-24).

**Nothing on today's page may be dropped.** `New-Problem-InfoMap` lists every item on today's
page (from `templates/target.html`, `templates/statement-panel.html` and `render.py`
`statement_panel`), where it is today and where it goes. Use it as the acceptance checklist:
one test per row that the item still renders.

#### 3.4.1 Order of the page

1. Breadcrumb; small caps "Erdős problem 257 · number theory".
2. **The statement as the headline**, typeset with KaTeX. Under it: status glyph and the stage
   mark; one sentence naming the stewards and how many statements are open; a note when the
   statement is unchecked ("Its review waits for the intent signer: 8 questions. Open the
   review →"), replacing the fidelity and review badges. Sources, steward dates and
   registrations in sidenotes.
3. "On this page": Proof · Not on a route · The statement and its review · Stewards, panel and
   write-up · What is known and tried · Record.
4. **§1 Proof** — routes, the selected route as a tree, the selected-statement panel (3.4.2–3.4.4).
5. **§2 Not on a route** (3.4.4).
6. **§3 The statement and its review** — the full informal statement and what the Lean means;
   a five-line review summary linking the review page; shared definitions as a folded list of
   links (never printed); the per-subject quality table folded.
7. **§4 Stewards, panel and write-up** — stewards and their commitment, panel members and
   motions, the eight-step write-up ladder. Controls only for those who may use them.
8. **§5 What is known and tried** — literature status, references, notes, plans, approach
   records, state of the problem, each folded with its count.
9. **§6 Record** — digestion, sources and licences, registrations, catalog evidence and drift,
   files and commits.

#### 3.4.2 §1 Proof: routes and the route tree (Mike, 2026-11-25)

- **Routes, two views**, switched by a Tree | List control in the Routes box:
  - *Tree* (`New-Erdos257`): today's selector — the small OR tree of route choices (F30) —
    kept and restyled. Numbered ends: ink for routes that prove the problem, rust for routes
    that would disprove it through a counterexample statement (`relation: refutes`), the
    selected end filled. Under it: "Drawn below ↓ Route 2 · …".
  - *List* (`New-Erdos257-List`): one row per route — kind (proves / would disprove), name,
    statements · proved · open, what it goes through, and Draw · Statements · Retire…. The
    selected row is tinted. The list replaces today's separate sets table.
- **Only the selected route is drawn, as a tree** (Figure 1, headed "Figure 1 · the selected
  route" and the route's name). The full 71-statement graph is never shown. The page opens on
  the route with the fewest open statements among those that prove the problem.
- **Fold proved statements**, on by default: proved siblings collapse into one dashed box
  ("14 proved · show") so open work stands out. Unfolded (`New-Erdos257-Unfolded`), a split
  with many holes is a boxed grid, and deeper levels under a cell show as "▸ 2 open below".
- **Retire** (shelve.js, `POST /shelvings` scope "route") on each list row and on the drawn
  route's header, only for a steward of the problem or a curator. The mockups are drawn
  signed in as a steward, and say so under the page heading.
- A statement used as a lemma from elsewhere shows as a dashed "uses: gap lemma" box beside
  its user (`uses` / `lemmas` in graph.json; `New-Erdos257-Route1`).
- A statement that has speculative statements proposed for it carries "+ 4 speculative ↓",
  linking to its group in §2.
- Keep `graph.js`'s hover (light a statement's lines) and click-to-select on the route tree.
- The route descriptions ("Fifteen special cases plus the rest") don't exist in the record
  yet. F29 already files a route's approach as a gloss; use that text when present, else
  "Route n".

#### 3.4.3 Selecting a statement, and the tabs

Every box in the route tree, and every statement in §2, is selectable. The tabs always belong
to exactly one statement:

- The selected box is **filled black**, and its path from the problem is drawn heavier.
- The tabs' **header is dark** and names the selection: "Selected in Figure 1 · Erdős problem
  257 › case split › A = primes". With nothing else selected it names the problem's own
  statement.
- The five tabs: **Claim · Proof · Known · Work · Record**, with counts for that statement
  in the labels (Proof 1, Work 3). "Work on this statement" and "Open its page" are always
  visible under the tabs. What each tab holds is part A of `New-Problem-InfoMap`; drawn for
  a hole in `New-Select-Every-Tab` and for the problem itself in `New-Erdos257-Panel-Tabs`.
- Two layouts — **Mike to choose** (§8):
  - **A, panel beside the tree** (`New-Select-Side`): a line runs from the selected box to
    the panel; the tree never moves. Recommended on desktop.
  - **B, record in place** (`New-Select-Inline`): the tabs open as a card directly under the
    box, pointing at it; the tree below moves down. Recommended on a phone.
- Esc, or clicking the selected box again, returns to the problem's own statement.

#### 3.4.4 §2 Not on a route

Every statement no route uses gets a home here, so §1 and §2 together place all 71 of
erdos-257's statements.

- **Speculative statements are drawn as small trees, grouped by the statement they were
  proposed for** (`proposed_for` in graph.json), with their own links (`deps`, `uses`,
  `lemmas`), in dotted outlines. Each group names its target and route ("For “every other
  infinite set” (Route 2)") and notes where a member is already used elsewhere (the Lambert
  identity by Route 6; the gap lemma by Route 1). A related result that rests on a
  speculative statement is drawn in its group.
- Then, as short lists: statements proposed for a target with no group of their own; related
  results (`relation: related`); special cases no split uses (`relation: partial`, not a
  hole of any route); superseded statements (`status: superseded`, with what replaced them).
- Each is selectable into the tabs, like a box in the route tree.

#### 3.4.6 On a phone (`New-Phone-Select`, `New-Phone-Every-Tab`)

- The route selector tree (300px) still fits and stays at the top of §1, with "Tap a numbered
  end to draw that route below" and the Tree | List switch.
- **The selected route is an outline, not a drawing**: statements top to bottom, indented by
  depth, joined by thin connector lines; proved siblings folded into one dashed box as on
  desktop. A drawn tree does not fit in 390px and must never scroll sideways.
- **Tapping a statement fills it black and opens its record directly under it** (layout B),
  with the same dark "Selected in Figure 1 · …" header, the five tabs (Claim · Proof · Known ·
  Work · Record, with counts), and "Work on this statement" / "Open its page". The outline
  continues below the card. Tapping the statement again closes it.
- Every touch target is at least 44px tall; the tab bar may scroll sideways inside the card if
  a statement's counts make it wider than the screen.
- Use one media query for this switch; the desktop layout (A or B, §8) stays as chosen.

#### 3.4.5 A problem with no work yet (`New-Problem-abc`)

The statement; a "What this problem needs" card (a steward · a check that the Lean says the
conjecture · a first attempt, each with its button); one box instead of the routes and tree,
beside the same tabbed panel, with empty states written as next steps; review, catalog
evidence and shared definitions (linked, never printed) folded in §2; people and write-up one
line each.

### 3.5 Steward pages (`mockups/New-Steward-Signup.dc.html`, `New-My-Problems.dc.html`, `New-Review.dc.html`)

These were designed from the code (`steward.js`, `me.js`, `session.js`, `panel.js`,
`words.js`, `literature.js`, `shelve.js`), not from a signed-in browser: the design session
wasn't signed in. Check each signed-in state against the live site.

- **Become a steward** (`/steward/<id>/`): the problem's statement; what a steward is (best
  efforts, no deadline, step down any time); the form (display name, optional page about you,
  the commitment tick box, "Become steward of <id>"); and **what happens next** as five steps —
  name goes on the problem → answer the review questions → confirm literature → approve words
  → sign the explainer and start the write-up. What you receive / don't receive in
  sidenotes. This is the onboarding: it tells a new steward their first jobs.
- **My problems** (`/me/`): per problem the steward holds, what is waiting, most urgent first,
  each a count + one sentence + one button: review questions (8 on erdos-257), literature
  proposals (22), words to approve (347 across 69 statements on erdos-257; 237 on
  erdos-1094). Then panel/write-up, update name, step down. Then open pull requests. Today the
  page lists every waiting section as one flat list (hundreds of lines); group by statement
  and let a steward approve all sections of one statement at once (words.js posts one
  approval per section today — check whether `POST /approvals` can take several; if not,
  that's an API task in the spec).
- **Review** (`/problems/<id>/review/`): a heading that says what it is ("Does the Lean say
  Erdős problem 257?") and who does what; a progress strip of the six stages; a "Your turn"
  note for the signed-in intent signer; the questions first — each with the statement and
  the variant side by side, the changed part highlighted, a plain sentence of what changed,
  the answer box and the source box; questions of the same kind grouped ("Questions 2–7:
  constant changes"). Candidates, pairs, tests, screens and signatures follow, folded, still
  labelled exhibits or judgements. A candidate's licence header is folded. The raw TeX in
  today's heading ("$A\subseteq\mathbb{N}$") renders.

## 4. Data change: crediting the people behind agents

Needs Mike's agreement before you implement it. It changes D-19 territory, so it goes
through the architecture document's own process (a proposed decision or overturn logged in
the spec, then a new version of `docs/architecture_decisions.html`) — never straight into
code.

### 4.1 What's true today
- AGENTS.md §"Getting a token (D-19)": "Identity is the human operator; agents are tools." A
  token is earned anonymously (prove the tutorial node, choose a pseudonym) or through GitHub.
  Ledger files are `ledger/<pseudonym>.json` with `identity` and `entries[]`; each entry may
  carry `automation: {framework, method, models[], tool_setup}`.
- In practice almost every agent run got its own pseudonym (`agent-a-a256a2`, `t1015c-a07`,
  `fable-1020-e257-a`, `opus-1124-sing`…): 140 identities, 461 entries on 2026-11-24. Most
  are Mike's own test and calibration runs. There is no field linking a pseudonym to a
  person.

### 4.2 Proposal
1. **One pseudonym per person.** Say so in the docs ("Use one pseudonym for yourself, not one
   per agent run") and in the token flow.
2. **Run labels inside entries.** Add an optional `automation.run` (string, ≤ 64 chars) to
   ledger entries, set from a new optional field on submit. The Contributors page lists runs
   under the person.
3. **Claiming old pseudonyms.** A new authenticated route, e.g. `POST /identities/merge`, with
   the token of the person's main identity as bearer and the token (or GitHub proof) of each
   identity to fold in. The result is recorded in the graph as a signed record (new schema
   `identity-links/v1`: `{primary, merged: [..], date, proof_kind}`) — ledger files are never
   rewritten, so history stays intact. The site groups by these records.
4. Schema changes follow the repo's rule that schemas are versioned and never edited
   (D-34): add new versions, don't change old ones.

### 4.3 Test identities
Mark calibration and test identities so the site hides them by default: either a list in
`policy.json` or a field on the identity. Today's obvious patterns: `t09xx-*`, `t10xx-*`,
`tester-*`, `calib-*`, `*-calibration-*`. Ask Mike to confirm the list — don't guess silently.

## 5. Keep in mind

- About says the network "keeps no leaderboard". Never rank people: no positions, no "top",
  sort by name or last activity.
- Anonymous contributors are first-class. Never require GitHub to be credited; only stewards
  and curators need GitHub (that's existing protocol).
- Every number on a page must come from the record at build time. No hand-typed counts.
- Accessibility: real `<button>`, `<a href>`, `<label>` + `<input>`; text contrast 4.5:1;
  visible focus ring in `--proved`; charts get a text alternative.
- Phone width (390px) must work on every page: no horizontal page scroll; wide tables scroll
  inside their own box; sidebars stack above content.

## 6. Bugs found in the review (fix regardless of the redesign)

| Where | Problem |
|---|---|
| `/problems/` on a phone | Page is 759px wide on a 390px screen — display maths and badge rows don't wrap. |
| `/problems/` | 113,000px tall: every problem with its full statement, no paging. |
| `/problems/` tabs | "All 445 · Open 602 · Proved 3" mixes statements and problems. |
| `/problems/abc/` (any problem with no work) | 19,500px: prints the full Lean source of every shared definition module (Weyl algebra, Milnor K-theory, simple graphs…) with Apache licence headers, none used by abc. Link them instead. Collapse the six empty sections into one "What this problem needs" card. |
| `/problems/abc/` | Title shows markdown asterisks: "\*abc\* conjecture". |
| `/problems/singmaster/` | Hole statements print raw LaTeX: `\{(n,k) : 1 \le k < n,\ \binom{n}{k} = t\}$…`. |
| `/problems/erdos-257/` | Subtitle prints raw `$A\subseteq\mathbb{N}$`. |
| `/problems/erdos-257/` | Main graph labels are about 9px and all 71 statements are drawn at once. Replaced by §3.4.2: one route drawn as a tree, proved statements folded, labels 12.5px. |
| `/problems/erdos-257/` on a phone | The graph is a cropped box you can't pan. On a phone show the route list and the selected statement instead. |
| `/rules/` | Table squeezed into the right half; the Value column wraps letter by letter ("da ys", "op en"); "the default (never changed)" wraps over five lines; left half empty. |
| `/docs/` | 73,700px, ~40,000 words, ~11px body text; inlines AGENTS.md. |
| `/contributors/` | 38,500px raw ledger tables keyed by run id; no stewards; no people. |
| Every page | Footer prints commit hashes and the list of source files in full. |
| Copy | Internal codes in reader-facing text: "D-19", "D-32 v3.17", "D-9 step 9", "attestation 000955", "admitted by motion:1". Move them to the record panel or a hover. |
| `/problems/erdos-257/` panel | "#1 Invite riversupport … passed, 0 yes · 0 no" — a motion shown as passed with no votes. Check the tally or the wording. |
| Sign in | Only GitHub is offered and nothing says contributing can be anonymous. Add one line under the button. |

## 7. Suggested order of work

0. Write the feature spec (§0.2). The direction (§2) is agreed; §8 has the questions left.
1. Tokens + header/footer (§2). Small, unblocks everything.
2. Bug fixes in §6 that don't depend on the redesign (maths rendering, asterisks, Rules
   table, phone overflow, footer disclosure).
3. Problems page (§3.2) including the JSON index.
4. Docs split (§3.3). Start with the sidebar + Overview + Quick start + Getting a token; move
   the rest section by section.
5. Contributors stage A (§3.1).
6. Write up the §4 proposal as a decision for Mike; after his yes, implement and ship
   Contributors stage B.
7. Problem pages (§3.4): the abc empty-state fix (3.4.5); then routes + route tree + fold
   (3.4.2); then selection and tabs (3.4.3, once Mike has chosen A or B); then §2 Not on a
   route (3.4.4). Check each row of `New-Problem-InfoMap` as you go.
8. Steward pages (§3.5) and Home (§3.0).

After each task: `make verify`, screenshots at 1440px and 390px into the evidence folder,
commit `FXX-Tn: …`, update the task ledger.

## 8. Open questions for Mike

- Selecting a statement: layout A (panel beside the tree), B (record under the box), or A on
  desktop and B on a phone?
- Should proved statements start folded for everyone, or should the choice be remembered per
  visitor?
- Which route should a problem page open on: the proof route with the fewest open
  statements, or one a steward pins?
- Which identities are test/calibration runs to hide by default?
- Should the 139 runs currently in the ledger be merged under `thisisanameforsure` once the
  merge route exists?
