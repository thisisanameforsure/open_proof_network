# Testers 2026-10-08: erdos-1094, consolidated and verified findings

Three background subagents, black box, from 12:56Z: A (MCP, root structure), B (HTTP, the
provable hole), C (site first, literature and words). All three stopped of their own accord by
14:11Z, each reporting that nothing cheap was left on the mathematics. Logs: `A.md`, `B.md`,
`C.md`; board: `COORDINATION.md`.

Verified by the lead from 14:12Z against the record (`origin/main` of the graph), the deployed
site and service, GitHub's run logs, and the network source. **C** = confirmed (how),
**C-code** = cause found in the source, **D** = by design (cite), **N** = not reproduced,
**X** = environment, **M** = the tester's own mistake.

## What landed

21 graph pull requests (#440–#460): 20 merged, 1 withdrawn by its author (#459, re-filed as
#460). None needed a human.

- **#441 (A)**: three-hole skeleton on the root. Its assembly does the floor/`max` case split and
  the finite union. The holes:
  - `--h1`: for each fixed k, finitely many n ≥ k² are exceptions.
  - `--h2`: exceptions with n ≥ k² have bounded k. This is the open Ecklund–Selfridge core.
  - `--h3`: exceptions with 2k ≤ n < k² have bounded k. This is a literature theorem
    (Granville–Ramaré 1996, Konyagin 1999) that nobody has formalised.
- **#450 (B)**: proof of `--h1`, so `--h1` is **proved**. The argument: m = k·⌊n/k⌋ is coprime
  to C(n,k) and divides k!·C(n,k), so n < k! + k.
- **#448 (A)**: partial on `--h3`. Lucas's theorem in the assembly leaves one hole, `--h3--h1`, a
  pure residue statement. It holds for every k ≤ 1000 with K = 58 (C's scan; last failure at
  (1579, 58)). Whether the papers prove exactly this form is unverified, because they are
  paywalled.
- **#457 (A)**: approach record for a dead residue-only route on `--h2`; small-k families defeat
  it.
- **C's words**:
  - Annexes: #440, #443, #444, #451, #460. They hold the literature survey, a fidelity reading
    that finds no defect, and an exception scan over k ≤ 200, n ≤ 2·10⁵ that finds exactly ELS's
    14.
  - Glosses: #442, #445–#447, #452, and second versions #454–#456.
  - Explainers: #449, #453, #458.
- **Root**: still open. A closing proof through the holes is fast-checked and kept in
  `A/root-closing-Proof.lean`. It can be sent once `--h2` and `--h3` are proved.

The lead's brief had the mathematics backwards. It called the n ≥ k² half Ecklund's theorem;
it is Ecklund's (and Selfridge's) open conjecture. C corrected it on the board at 12:57–12:59Z,
before any Lean was written.

## P1

1. **A hole written by a merged partial cannot be prechecked until some later merge re-renders
   the products.**
   - **Status:** C (record, two instances), C-code.
   - **What the record shows:** bot commit `28f5a569c` (`gate: #441 pass`) writes `--h1/2/3`.
     Its `frontier.json` lists all three, but `rendered_from` is its parent `d1833c0ed`, whose
     tree holds only `erdos-1094`. The same happens at `bc3f897b9` (`--h3--h1`, rendered from
     `cf8fd082a`).
   - **Cause:** `api/opn_api/precheck.py:505` `rendered_from()` pins the job to `graph.json`'s
     `rendered_from`, which is the merge commit. The post-merge job writes the holes in the
     commit *after* it, so no rendered commit ever contains a freshly written hole.
   - **Cost:**
     - Each precheck runs 6.5 minutes and fails step 2 `layout-missing`. B paid this twice, and
       the error does not say why.
     - On a quiet network the hole stays unprecheckable indefinitely. Only a merge somewhere
       re-renders the products. This time C's annex merges happened to do it.
   - **Fix direction:** pin a job for a node to the commit that *carries* the products (the bot
     commit), not the commit they were rendered from. At the least, refuse at once with a named
     error when the node's directory is absent at the pinned commit (B-F2, C-F5).

## P2

2. **The site misstates who did what on erdos-1094.** This breaks "published state is actual
   state".
   - **Status:** C (site, on 14:15Z pages), against attestations `000441`/`000450` and
     `ledger/t1008-a.json`.
   - **The partial assembly panels** on `/nodes/erdos-1094/erdos-1094/` and
     `/nodes/erdos-1094/erdos-1094--h3/` say "author not recorded" and "No attestation covers
     it". But `attestations/000441.json` has `submitter: t1008-a, verdict: pass,
     node_id: erdos-1094`, and the ledger credits both partials.
   - **The proved hole's page** `/nodes/erdos-1094/erdos-1094--h1/` never names its prover. The
     Attestation block shows toolchain, Mathlib and steps but no submitter; the only names on
     the page are the gloss writer's. (Reported as A3, C2, B6.)
3. **Every honest one-hole reduction is claimable as circular.**
   - **Status:** D (design gap), owner's call.
   - **The problem:** the circularity rule's exhibit is "hole implies ancestor". For a one-hole
     skeleton the assembly *is* that proof, so the exhibit always exists. B wrote and prechecked
     (pass) a one-hole partial on `--h2` that records the kernel-checked fixed-k bound and
     reduces the core to a finite window per k. B withheld it for this reason, and A agreed.
     The record therefore has no way to say "this is a genuine reduction" (A-F1/F3, B-F1,
     C13, C-F9).
   - **Needed:** a ruling on whether a reduction that strengthens or localises its parent
     counts as progress, and if so, how it is marked.

## P3

4. **The guide says the skeleton's annex citation is enforced mechanically; the gate does not
   require one.**
   - **Status:** C (record).
   - **Evidence:** the guide, line 1115 ("Three rules the gate enforces mechanically") and line
     1122 ("The skeleton cites the annex it came from"). Both merged skeletons (#441, #448)
     carry no `-- annex:` line. The gate checks a citation only when one is present.
   - **Decide** which is right, then fix the other. (A5)
5. **The `__` naming warning is dropped only for the node's own declaration.**
   - **Status:** C-code.
   - **Cause:** `without_generated_name_warning` (`api/opn_api/checks.py:738`) compares against
     `node_id` exactly. Hole theorems that arrive through an inlined `Context.lean` keep the
     warning, and the root's Context has three.
   - **Fix:** the guide's sentence covers every gate-generated hole name; the filter should match
     any `<node>__h<n>` declared in the inlined Context. (A4)
6. **Annex provenance is truncated on the site.**
   - **Status:** C (site).
   - **Evidence:** the root record page reads `sources read via erdosproblems.com,, 2026-10-08…`.
     The annex's `model_and_tooling` is a folded YAML scalar, and only its first physical line
     is shown. (C4)
7. **Outline titles are cut mid-word on the problem page.**
   - **Status:** C.
   - **Example:** "…an equivalent form that may help deco". (C5)
8. **A double full stop on the problem page.**
   - **Status:** C.
   - **Example:** "…with only finitely many exceptions.. Imported from formal-conjectures". The
     informal statement ends in a full stop and the template adds another. (C9)
9. **A carried witness keeps its `-- hole: h_fixed_k` line** at the top of the record's
   `Witness.lean`.
   - **Status:** C, cosmetic. (A7)
10. **An approach record's `blocked_on` is capped at 200 characters**, and the guide's
    description of the field (line 1044) does not say so. The error itself is clear.
    - **Status:** C (guide). (A9)
11. **Not re-run**, from the logs only:
    - `div-zero` flags `n % p` with `Nat.Prime p` in scope (A).
    - `waiting_on` can be stale in the submissions list (C7).
    - The guide's `closing` block (line 1276) is reachable only through MCP `get_node`, with no
      HTTP route (B5).

## Not bugs

- **Two-band latency (B1, B4, C3, A2).**
  - **Status:** X.
  - **Measurement:** of twelve `GET /submissions/44x` calls, nine took under 1 s. The three slow
    ones spent their whole time in TCP connect (`time_connect` 75.2 s, 19.1 s, 19.2 s) before
    any byte reached the service.
  - **Cause:** this is macOS's SYN retransmission schedule on this laptop's path to API Gateway,
    the same finding as 2026-09-21. B4's log record (`latency_ms` 1758, created about 75 s
    late) fits it. It is worth knowing that every locally run agent pays it.
- **Outline commits force a gate round (A8, C12).**
  - **Status:** D, misattributed.
  - **What happened:** the merge actor counts `targets/<id>/outlines/` as a rendered product
    (`.github/workflows/merge.yml:153`). #450's second update (13:50:43Z) followed #448's bot
    commit `bc3f897b9`, which wrote `--h3--h1`'s files and changed `--h3/Context.lean` on the
    same target. The guide says a hole written by a partial costs one round (line 816).
- **Green appends waited behind #450 (C11).**
  - **Status:** D.
  - **Actor log** (run 37786220979): "#450 is up to date and its gate is running: holding its
    lane", then "green; the host is still computing whether it conflicts". The guide says an
    annex can wait one round behind a proof on its target (line 817). The 7-minute
    `mergeable: null` is GitHub's. It is a throughput request (C-F6), not a defect.
- **The service stored different text from JSON with raw newlines (C10).**
  - **Status:** N.
  - **Test:** a raw newline inside a string answers `400 malformed-body` at `POST /check`. Every
    route parses with one strict `json.loads` (`api/opn_api/identity.py:120`). C's mangled
    glosses came from zsh `echo` (M, C's own entry).
- **The naming warning is not dropped without a `node_id` (B2).**
  - **Status:** M.
  - **Cause:** B's file declared `Opn.erdos_1094__h1`. The gate writes the hole as
    `erdos_1094__h1`, and the filter drops only that name, with or without a `node_id`. Item 5
    is the real gap.
- **`list_words_needed` omits the root's statement (C8).**
  - **Status:** D. A root's words are its curated informal statement, as the guide says and
    W1 noted on 2026-10-06.
- **"get_node lag of 11 minutes".**
  - **Status:** X. The cause was A's own TLS and route failures; merge to a usable node took
    about 7 minutes.

## Feature requests, consolidated

Ranked by how much each would have changed this run.

1. **Precheck refuses at once when the node is absent at the commit it would run at** (B-F2,
   C-F5), together with fix 1.
2. **A reduction artifact, or a circularity carve-out for it** (A-F1/F3, B-F1, C-F9). This is
   what item 3 would build.
3. **A literature-status label on a node**: open, known but unformalised (with references), or
   elementary (A-F2, C-F2/F8). Today `--h2` (open) and `--h3` (a theorem) both read "open".
4. **A prior-art record type that is not an outline** (C-F1). A literature survey filed as an
   annex is listed under "Outlines … not followed by any merged decomposition".
5. **A skeleton dry run** that returns the holes and their expected witness types without a
   six-minute precheck (A-F4).
6. **Show hole names** (`h_fixed_k`, `h_large_n`) on the site (C-F3).
7. **Link a merged skeleton to the outline it followed, after the fact** (A-F5). C's stepped
   annex names A's holes exactly, but #441 merged first.
8. **Refuse an exact duplicate at precheck, not only at submit** (A-F6).
9. **The fast check warns when a closing proof uses holes not yet proved** (A-F7).
10. **Appends overtake a proof's lane hold** (C-F6).
11. **Outline steps for an assembly's closing tactics**, so an explainer can anchor them
    (C-F4).

## Outcomes (second sitting, 2026-10-08, branch `testers-1008-fixes`)

The owner's rulings: fix P1 with feature 1 folded in, and P2 item 2 (site credit); P2 item 3
(circularity) is the owner's to decide, so it was broken down for him and no code changed;
reproduce every P3 item as a failing test before fixing; feature 2 is explained (it is the
circularity question); feature 3 is wanted, so it is to be planned; feature 4 is dropped,
because prior art belongs in the literature review.

| Finding | Task | Outcome |
|---|---|---|
| P1 fresh hole unprecheckable (+ feature 1) | F06-T14, Q19 | red 4 → green; `409 products-pending` before any job; live at api deploy |
| P2 site credit | F04-T35, Q36 | red 4 → green; the lead's full live-graph render found "nothing has been merged" beside a merged partial, red 1 → green; screenshots read |
| P2 circularity | — | owner's call; breakdown given (D-12 #4 `reduction` vs the v3.21–v3.23 claim) |
| P3-4 annex citation | F10-T18, Q24 | guide drift only (gate matches D-12/D-31); guide test red → green |
| P3-5 `__` warning on inlined holes | F13-T32, Q33 | reproduced live on `--h3`; red 4 → green |
| P3-6 annex provenance cut | F04-T36, Q37 | red → green (YAML `BaseLoader`; 17 of 64 live labels had been cut) |
| P3-7 outline titles mid-word | F04-T36 | red → green (19 live titles) |
| P3-8 double full stop | F04-T36 | red → green (16 pages) |
| P3-9 `-- hole:` line in Witness.lean | F07-T75, Q79 | red 12 → green; targeted lean tier passed; live at re-pin |
| P3-10 `blocked_on` cap undocumented | F10-T18 | guide states every cap, read from the schema by the test |
| P3-11 div-zero on `n % p` | — | reproduced with the real checker; by design (F02-R2/Q3: divisor text only, acknowledge it); a hypothesis-aware `div-zero@v2` is the owner's call |
| P3-11 stale `waiting_on` | — | not a defect: the read was during the gate (F05-Q19 documents the last read); guide sentence added |
| P3-11 `closing` over HTTP | — | not a defect (D-28: raw files; F04-Q27/F09-Q13); guide says how to read it from `Statement.lean` |
| new: a cap inside `oneOf` echoed the text | F07-T74, Q80 | found writing F10-T18; red 1 → green |
| new: "Three rules" over five bullets | F10-T18 | red → green |

Not done here: the live deploy (api push, site deploy) and the graph re-pin that carries the guide
and F07-T75, both waiting on the owner because local `main` carries another session's unpushed
commit (Decisions v3.34).

## Third sitting (decisions v3.35)

P2 item 3 and feature 3 were built on the owner's rulings: a merged circularity claim is a label
(F08-T39, F03-T18, F10-T19, F04-T37), and a node carries a literature status proposed by anyone and
confirmed by a steward or curator, who are told through `/me/` (F08-T40, F05-T29, F23-T12,
F09-T24, F04-T38). Feature 2 is covered by the first; feature 4 was dropped.

Found on the way, open: `/problems/erdos-1094/` measures `scrollWidth` 779 at 390 px — an
unwrapped source URL and the statement-QA table's columns (the F04-T37 agent, pre-existing).
