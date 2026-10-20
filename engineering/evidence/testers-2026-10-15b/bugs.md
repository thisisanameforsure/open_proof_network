# Findings, testers 2026-10-15b (lead's consolidation, checked where marked)

## Outcome
Graph PRs, all opened through the MCP with no human: #538 annex `--h3`, #539 skeleton `--h3` (holes `h_els`,
`h_gr`), #540 partial `--h2--h2--h2--h3--h1--h1--h1` (Konyagin core, hole = vdT `small_integer_linear_relation`),
#541 annex `--h3--h3`, #542 skeleton `--h3--h3` (holes `h_cheb`, `h_sander`), #543 partial `--h3--h2` (ELS split into
three ranges) all MERGED; #550 complete proof of `--h2--h2--h2--h3--h1--h1--h1--h1` (the lattice node, S and T's
joint 158 kB port) OPEN at 14:58Z. Checked with `gh pr view` at 14:58Z.

The paper's chain (H, `GR-OUTLINE.md`): Theorem 8 (preprint p. 5) gives h3 from [ELS 1993] plus Sander's
equidistribution bound (5.1) and a last-digit carry step; it reaches `--h3--h1` only for n ≳ k²/log k.

## Not network defects
- **The 13:41–14:36Z stall that every agent reported was the laptop.** `pmset -g log`: "Entering Sleep state due to
  'Low Power Sleep' … Using Batt (Charge:1%)" at 16:41:36 +0300 (13:41:36Z), "Wake from Hibernate" at 17:36:21 +0300
  (14:36:21Z). Graph CI ran gate and merge jobs normally inside the window (13:43, 13:46Z). This explains G's hung
  calls, H's hung prechecks, S's 55-minute poll and T's 3339 s tool call and hour-long "running" precheck. Checked.
- ams.org and renyi.hu refuse scripted downloads of ELS; the Wayback Machine copy works (G).
- `φ` is `Nat.totient` notation under `open scoped Nat` (T). A guide sentence at most.

## Network findings
1. **#543 merged without its holes' witnesses, so its three children are `blocked`** (`--h3--h2--h1/2/3`, read from
   `graph.json` at origin/main). H dropped the witnesses because the re-precheck carrying them hung in the sleep. The
   witnesses are trivial (`True`; `⟨1, one_pos⟩` for ∃ c : ℝ, 0 < c) and need `propose_witness`. Not a defect; an
   open item. Checked.
2. **Fast check and gate disagreed on an instance** (T). `gramDet_le_prod_sq_norms` fast-checked clean; precheck
   step 4 refused it with `failed to synthesize LE (Matrix (Fin m) (Fin m) ℝ)` (`T/precheck-v1.json`, lines 30, 94:
   checked). The fast-check side's receipt came back after the sleep and is not saved, so the disagreement is
   reported, not shown. Likely cause: the hosted checker's Mathlib is the one nearest the pin, not the pin.
3. **A claim on a node someone else holds answers 201** and names the holder only in `others` (G, on `--h3--h2`, H
   first). No receipt saved for that call; G's `claim-h3.json` shows the shape (`others: []`). Reported, not shown.
4. **`409 products-pending` for a new hole** at 13:39:31 and 13:41:32Z after #542 merged at 13:38:49Z
   (`G/claim-h3--h3--h2-attempts.txt`, checked); the bot commit's gate push ran 13:43:27Z. Expected behaviour; H
   called the message good.
5. **The fast check cannot see one heavy declaration** (504 even alone); T cut `successive_minima_inductive_step`
   into 27 sorried `have` blocks to check it. Second run in a row to ask for a per-declaration mode.
6. **A hole is closed over every binder in scope** (S): a `have` after the `intro`s dragged 30-odd parent variables
   into the hole's statement, and the precheck passed. Wants a guide sentence ("state holes before intro").
7. **A precheck's answer prints the tutorial nonce** (G). By design for earning a token; noted because it reaches
   the terminal.
8. **An Aristotle batch from another session was working a node S held a claim on** (T). Not checked which node;
   `opn_prove` attempts filed 06:27Z exist on `--h3--h1--h1--h1` (h3 subtree). Unverified.

## Left
- #550 to gate and merge; then `--h2--h2--h2--h3--h1--h1--h1` should close via #540, and its parents via the closer.
- Witnesses for #543's three holes.
- Drafts not submitted: `G/skeleton-h_sander-draft.lean` (hole: GR Lemma 5.1), `H/h_cheb-partial-draft.lean` (hole:
  PNT for `Chebyshev.theta`, absent from the pinned Mathlib).
- Every remaining hole in the h3 subtree is deep: PNT in short intervals, Sander's exponential sums, Ingham,
  Ecklund–Erdős–Selfridge's g(k) > k^{1+c}.
