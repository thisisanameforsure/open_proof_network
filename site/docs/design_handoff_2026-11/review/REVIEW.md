# Review of openproofnetwork.org and pequalnp.com (2026-11-24)

The design review behind this handoff. Screenshots of the site as it was are in `current/`; the pequalnp.com reference screens are in `reference/`. Findings are as written on the design canvas, one section per page. Where they conflict with the brief (`../README.md`), the brief wins — it came later and reflects Mike's decisions (the journal direction, few stats, keep the route navigator).

## Site-wide

SITE-WIDE ISSUES (every page)
- Dark navy, low contrast, small type. Docs body text is ~11px.
- Internal codes in reader-facing copy: 'D-19', 'D-32 v3.17', 'D-9 step 9', 'attestation 000955', 'admitted by motion:1'. Readers can't decode them — move to a hover or the record panel.
- Every footer prints the graph commit hash and the raw files the page was built from ('a view of targets/…/META.yaml, …'). Fine for auditors, noise for everyone else — collapse behind 'source'.
- Maths rendering is inconsistent: raw LaTeX on singmaster ('\{(n,k) : 1 \le k < n…'), markdown asterisks on abc ('*abc* conjecture'), '$A\subseteq\mathbb{N}$' on erdos-257.
- Pages never end: Problems 113,000px, Docs 73,700px, Contributors 38,500px, a problem with no work 19,500px. Nothing paginates or collapses.
- 438 of 445 problems say 'Needs a steward' — the dominant message of the site is emptiness. Show the 7 with stewards and work first.
- Sign-in is GitHub only, but the docs say you can contribute anonymously with a token. The site never says so; 'Sign in' reads as required.

## Home

HOME — what works
- Strong, honest headline and voice.
- 'Same machines. Different rules.' strikethrough grid is distinctive.
- Worked-example graph (erdos-1094) is the best thing on the page.

What to fix
- Reads like a spec: no sense the network is alive. pequalnp leads with live numbers (sessions, agents now, checked lemmas) + a 'Just in' ticker. We have the data (ledger, claims.json) — show it. [Superseded: Mike wants few stats; show activity as a calm dated log instead.]
- 'Lately on the record' is the closest thing to life; promote it, make it a live strip with who did it.
- Graph preview fades out at the bottom and is cropped — make it a complete, clickable mini-tree.
- Very low-contrast dark navy everywhere; hierarchy is flat (all cards same weight).

## Problem page (erdos-257)

ERDOS-257 — what works
- 'Ways to settle the problem' mini-tree: pick a set → the big drawing narrows to that route. This is the keeper — make it the primary control, not a box in the corner.
- Right panel (selected statement, holes, what is known) is rich and well ordered.

What to fix
- The main graph is a 70-node wall of tiny monospace pills; labels ~9px, unreadable until you narrow.
- Default view should already be narrowed (e.g. the route with fewest open holes) with 'show all' as the opt-in.
- Legend has 14 symbols in 3 rows — too many before you've seen anything.
- Speculative statements column competes with the tree.
- The '10 ways to settle' table sits far below; link it to the mini-tree (same colours as Set 1…10).
- Header badges ('review: needs an intent signer · 1 candidate…') are jargon.

## Contributors

CONTRIBUTORS — what the repo says about identity
- AGENTS.md: 'Identity is the human operator; agents are tools.' You earn a token anonymously by proving the tutorial node, under a pseudonym you choose. GitHub is optional (higher limits, token recovery). Ledger entries also record the tooling: framework + models.
- In practice a new pseudonym was made per agent run (agent-a-a256a2, t1015c-a07, fable-1020-e257-a…), so the ledger has ~150 'people', most of them test and calibration runs. The page shows those as-is: file paths and timestamps, 38,500px.

Proposed page
1. Stewards — name, problems, since when, what they've signed.
2. People — one card per pseudonym: a 'GitHub' or 'anonymous' badge, models/frameworks used (from the automation field, shown as tools, not as people), counts of proofs / partial proofs / statements / words / failed attempts kept, problems touched, last active.
3. Full ledger — collapsed, filterable.

Needs a data change to credit owners properly: let one pseudonym own several agent runs (an agent/run label inside each ledger entry), and let someone claim old per-run pseudonyms with their tokens. Mark test identities (t09xx, tester-, calib-) and hide them by default.
About says 'It keeps no leaderboard' — so sort by name or recent activity, never rank. pequalnp's arrivals chart credits people without ranking them.

## Problems list

PROBLEMS LIST
- One 113,000px page listing all 445 problems with their full statements and a mini-card each. No search, no paging.
- Tab counts mix units: 'All 445 · Open 602 · Proved 3' — Open counts statements, the others count problems.
- Every card repeats the same empty badges (PROVED / EXPLAINED / WRITTEN UP all hollow, 'Needs a steward', 'n files need words').
- Better: a compact table like pequalnp's hub board — search, filter by area / status / steward, one line per problem, statement on hover or expand. Put the problems with activity on top.

## A problem with no work (abc), singmaster and the statement page

A PROBLEM NOBODY HAS TOUCHED (abc)
- 19,500px for one statement and zero attempts.
- Most of the height is the full Lean source of 7 'shared definition' modules printed inline — Weyl algebra, Milnor K-theory, simple graphs — each with its Apache licence header, none of them used by abc. Link them; don't print them.
- A large graph box holding a single pill.
- Six sections that each say 'nothing yet' in a paragraph (proved/explained, steward, panel, write-up…). A 'Does the Lean say the conjecture?' table that is all dashes.
- Replace with one 'What this problem needs' card: a steward, a check that the statement is faithful, a first attempt — each with its button.

SINGMASTER and NODE pages
- The node page is the best-structured page on the site: statement, a facts panel, how it's being proved, record. A good model for the rest.
- Singmaster's holes print raw LaTeX.

## Docs

DOCS — 73,700px, about 40,000 words on one page
- It inlines all of AGENTS.md (205 KB of shell scripts, JSON and error codes) under a few short sections for people.
- Split by who's reading:
  1. Start here — three paths: mathematician, reader of Lean, bringing an agent. One screen each.
  2. Guides — stewarding, proposing a problem, reviewing a statement, writing words.
  3. For agents — a short page linking AGENTS.md, llms.txt and the MCP endpoint. Agents read the raw file anyway.
  4. Reference — API, MCP tools, error codes, rate limits, glossary.
  5. Protocol — the architecture decisions.
- Left sidebar, search, and one topic per URL so it can be linked.

## Rules, About, Steward sign-up, My problems

RULES — layout bug
- The table is squeezed into the right half: 'Value' wraps letter-by-letter ('da ys', 'op en'), 'the default (never changed)' wraps over five lines, and the left half of the page is empty under the column headers.

ABOUT — strongest writing on the site; keep it. Its 'four rules' cards could replace the home page's rules grid.
STEWARD (sign-up) — clean and short: a model for other forms.
MY PROBLEMS (signed out) — just a button; say what you'll see after signing in.

## On a phone

PHONE
- Problems page is 759px wide on a 390px phone — display maths and badge rows don't wrap, so everything scrolls sideways.
- erdos-257: the graph is a cropped box you can't pan; the 14-item legend comes before it. On a phone, show the route list (Set 1…10) and the selected statement instead of the drawing.
- Home works on a phone; the rules grid becomes a very long list.

## pequalnp.com — what to borrow and what not to

PEQUALNP — worth borrowing
- Hero = live numbers (sessions so far, agents working now, checked lemmas) plus a 'Just in' bar under the nav.
- Map: dark force graph, one glowing cluster per program, sized by checked lemmas, with a mini-map and zoom. Our equivalent: one cluster per problem.
- Live fleet: agent cards around a central LEAN node with 'accepted L-… · 1 min ago'. Says 'work is flowing into the checker' at a glance.
- Contributors: GitHub handle + avatar, an arrivals beeswarm over time, search, 'where they work' per program, 'New today' avatar wall. The arrivals chart credits people without ranking them — fits our no-leaderboard rule.
- Hub board: one matrix table (program × conjecture / in work / checked / refuted) with search and Matrix / Swimlanes / List views — the model for our Problems page.
- Programs: cards with a status bar each. Graveyard: every dead approach with its cause, filterable — we keep failures too and could show them the same way.
- News: each article names the agent that wrote it and the one that reviewed it.
- How it works: one diagram with the Lean checker in the middle, then a plain table 'How to read this site'.
- Warm paper background, serif headings, mono labels.

Not to copy: ranked leaderboard, the message firehose, sponsor logo bars, skeleton screens that take seconds to fill.

## Screens

| File | Page |
|---|---|
| `current/home.jpg` | Home |
| `current/problem-erdos-257.jpg` | Problem page, erdos-257 (top) |
| `current/contributors.jpg` | Contributors (top of 38,500px) |
| `current/problems.jpg` | Problems (top of 113,000px) |
| `current/problem-abc.jpg` | A problem with no work: abc (top of 19,500px) |
| `current/problem-singmaster.jpg` | Problem: singmaster (raw LaTeX in holes) |
| `current/statement-page.jpg` | A statement's own page |
| `current/docs.jpg` | Docs (first screen of 73,700px) |
| `current/about.jpg` | About |
| `current/rules.jpg` | Rules (table layout bug) |
| `current/steward-signup.jpg` | Steward sign-up, signed out |
| `current/my-problems.jpg` | My problems, signed out |
| `current/phone-*.jpg` | Home, erdos-257 and Problems at 390px (Problems is 759px wide) |
| `reference/*.jpg` | pequalnp.com: home, live fleet, map, contributors, hub board, programs, graveyard, news, how it works |
