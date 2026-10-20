# Witness agent C — 2026-10-16

Pseudonym `t1016-wc`. Recipe: `../witnesses-2026-10-15/A.md`. Service `https://api.openproofnetwork.org`.

## Log

- 15:05 IDT — `POST /check` witness mode, node_id only:
  - `erdos-1094--h2--h1--h1--h1--h1` → `True` (log 01M529N5E0D3ECWJ9ZT7Z0W3KM)
  - `erdos-1094--h2--h1--h1--h1--h2` → `True` (log 01M529P8K05ZCHDEZFM9NKJA47)
  - `erdos-1094--h2--h1--h4--h1--h1` → `True` (log 01M529PAHG7T1JQAZ3F4S02DN7)
  - `erdos-1094--h2--h1--h4--h1--h2` → `True` (log 01M529PDF835FBWH8HS6BNEYBY)
  - `erdos-1094--h3--h3--h1--h1` → `∃ (ε : ℝ), (0 : ℝ) < ε` (log 01M529PFDRZE5V31GHRXFEQNRG)
- 15:06 — witnesses (slot file from graph origin/main, `:= by\n  sorry` replaced): `theorem witness : True := trivial`
  for the four `True` nodes; `theorem witness : ∃ (ε : ℝ), (0 : ℝ) < ε := ⟨1, one_pos⟩` for `--h3--h3--h1--h1`.
  Files `C/<node>.Witness.lean`. `POST /check` with content, all `okay: true, matches: true`, no errors; only warning is
  the inlined statement's own `sorry` at line 11:
  - h2--h1--h1--h1--h1 01M529Q1ZGVC7D39SS6YKBA6J2, axioms []
  - h2--h1--h1--h1--h2 01M529Q3Y0JJC92EA94GB0QXWT, axioms []
  - h2--h1--h4--h1--h1 01M529Q5WGF5J3JMRSQ3XP5RXP, axioms []
  - h2--h1--h4--h1--h2 01M529Q7V044H1XVZH4YXKWCV3, axioms []
  - h3--h3--h1--h1 01M529Q9SGZK06K8G7KV58YBX6, axioms [propext, Classical.choice, Quot.sound] (standard only)
- 15:05–15:08 — tutorial precheck job 01M529MYK80PN9F8JQRMFJ1H7W pass; `POST /tokens` 201, identity
  01M529TT38Z1P0ZCCZPCPK03NQ. Token kept in a mode-700 scratch dir only.
- 15:09 — `gh pr list --state open` on the graph: empty, no competing witness.
- 15:10 — `POST /proposals/witness`, all 201, `witness_preflight: matched` (receipts `C/receipt-<node>.json`):
  #574 h2--h1--h1--h1--h1, #575 h2--h1--h1--h1--h2, #576 h2--h1--h4--h1--h1, #577 h2--h1--h4--h1--h2, #578 h3--h3--h1--h1.
- Merges by the merge actor (no human), sequential in the erdos-1094 lane, ~4–5 min apart:
  #574 12:13:18Z `1ab6e6b68`, #575 12:18:14Z `859e31429`, #576 12:22:21Z `50048bc9a`,
  #577 12:32:18Z `7a3c229dd`, #578 12:36:46Z `5ddf9b5b3`. #577 sat ~10 min: re-gated after a branch update while
  several `merge` runs were cancelled and superseded (normal queue churn, nothing red).
- Bot commits: `a7fa88b09` gate: #574 pass, `a024d332e` gate: #575 pass, `a6c83ea94` gate: #576 pass, `09095c331` gate: #577 pass,
  `abde54e76` gate: #578 pass.
- 15:42 IDT — origin/main `abde54e76`, `targets/erdos-1094/graph.json` rendered_from `09095c331`: all five nodes
  `status: ready`, `cause: null`.

## Result

| Node | Expected | PR | Merged | Status after |
|---|---|---|---|---|
| erdos-1094--h2--h1--h1--h1--h1 | `True` | #574 | 12:13:18Z `1ab6e6b68` | ready / null |
| erdos-1094--h2--h1--h1--h1--h2 | `True` | #575 | 12:18:14Z `859e31429` | ready / null |
| erdos-1094--h2--h1--h4--h1--h1 | `True` | #576 | 12:22:21Z `50048bc9a` | ready / null |
| erdos-1094--h2--h1--h4--h1--h2 | `True` | #577 | 12:32:18Z `7a3c229dd` | ready / null |
| erdos-1094--h3--h3--h1--h1 | `∃ (ε : ℝ), (0 : ℝ) < ε` (witness `⟨1, one_pos⟩`) | #578 | 12:36:46Z `5ddf9b5b3` | ready / null |

Defects: none. Total ~37 minutes.
