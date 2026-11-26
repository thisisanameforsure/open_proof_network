# REPORT — t1125-257, session 2, on erdos-257 (23:05Z–00:05Z)

## 1. Mathematics

### Choice of hole
I read all six refutes-side holes the brief named, with their attempts and annexes.

| hole | what it says | verdict |
|---|---|---|
| `variant-cce9b284--h2--h1` | an even-denominator rational whose floor-multiplicity walk has finitely many defects | An even denominator means the walk never ends at 0, because every 1/(2^m−1) has an odd denominator. So a finite defect set needs an infinite subsum with rational value, which is the refutation itself. The postmortem already on the node says the same. |
| `variant-cce9b284--h2--h4` | infinitely many repairs with a rational repair sum | The repair terms are ≥ 0 and their partial sums are bounded by x, so the series is summable in Lean and the tsum = 0 junk value gives no loophole. The sum is x − Σ_A, so the hole is again "Σ_A rational for an infinite A". |
| `spec-a70fcca4-v2--h3` | carries for 1/2 controlled by C(j+1) | The hole forces Σ_A 1/(2^a−1) = 1/2, which is the refutation in a stronger form. |
| `variant-cce9b284--h11` | for some j, a calm-point chain | It implies Dickson prime pairs (q, 2q−1) or (q, 4q−1) in every dyadic interval. Merged node spec-5e932b4b plus two annexes. |
| window rungs `--h4--h1--h1--h1`, `--h4--h1--h2--h1` | after a skip at m > 100, another skip within 2m or 3m+2 | These are statements about every digit of the 1/2 walk. The Liouville, carry and invariant routes are all recorded as dead. |
| **`spec-a70fcca4--h4--h2`** | **the greedy walk of 1/2 skips infinitely often** | **Picked.** Its only route, from t1026-a, went through the window `--h4--h1--h2`, which is strictly stronger than the gap bound. |

### What I proved (a partial on `spec-a70fcca4--h4--h2`)
Notation: r is the greedy remainder of 1/2, t_n = 1/(2^n−1), and T_{k+1} = Σ_{n>k} t_n.

1. The walk skips step 1, because r_1 = 1/2 < t_1 = 1.
2. Suppose the walk never skips after some m. Let k be the last skip in [1, m]. Every step after k is taken. So r_{k+1} = r_k, and Σ_{i<K} t_{k+1+i} = r_k − r_{k+1+K} ≤ r_k for every K, since every remainder r_n is at least t_n ≥ 0. Hence T_{k+1} ≤ r_k.
3. The gap bound `spec-a70fcca4--h4--h1` gives r_k ≤ 2^{−k} + 4^{−k}/3. That is at most T_{k+1}, because termwise t_n ≥ 2^{−n} + 4^{−n} (proved with geometric tsums). So T_{k+1} = r_k.
4. r_k is rational, by induction on the walk. T_{k+1} equals E minus a finite rational sum, where E = Σ_{n≥1} 1/(2^n−1). The series is summable via t_n ≤ 2·2^{−n}, then `sum_add_tsum_nat_add` and `Irrational.sub_ratCast` finish the step. And E is irrational: **`variant-2f5236aa`, already proved on the graph**, used through `import Nodes.«variant-2f5236aa».Proof`. Contradiction.

The partial has **one hole**, `hgap`, whose statement is exactly `spec-a70fcca4--h4--h1`. Everything else is proved in Lean: steps 1–4, the tail-irrationality lemma and the bound 2^{−k} + 4^{−k}/3 ≤ T_{k+1}.

What this changes in the graph, honestly stated:
- **`--h4--h2` now follows from the gap bound `--h4--h1`.** Before, its only route needed the strictly stronger window `--h4--h1--h2`; t1022-j's postmortem shows the window implies the gap bound but not conversely.
- The proof also formalises the converse direction that t1026-a's postmortem stated only in words: a bound of the `--h4` type implies skips infinitely often, given Erdős 1948.
- **It adds no new sufficient set for the refutation.** `--h4--h1` already closes the parent `--h4` by route @1. The open mathematics on this branch is unchanged: the gap bound, equivalently the window rungs, all statements about every skip of the 1/2 walk.

Intermediate versions, all prechecked and passing, none submitted:
- v1: holes "every tail irrational" and "no stall".
- v2/v3: holes "every tail irrational" and the skip-gap bound r_k ≤ T_{k+1}. The skip-gap hole is equivalent to `--h4` itself, since `--h4` says r_m ≤ T_m for all m. Submitting it would have made a near-cycle h4 → h4--h2 → (h4 restated), so I did not.
- v4: the Erdős hole reduced to the constant E. The gate answered `restates: "variant-2f5236aa"`, which is how I found that node is already proved.

Numerical check (local Python, exact Fraction walk, tails to 1300 digits): to n = 1500 the walk of 1/2 has 767 skips, and r_k ≤ T_{k+1} at every one of them. The smallest margin (T_{k+1} − r_k)·4^k is 0.4268, at k = 1.

What is left open on this branch: `spec-a70fcca4--h4--h1` (the gap bound) and its window rungs `--h4--h1--h1--h1` and `--h4--h1--h2--h1`. All of them say that no skip of the 1/2 walk lands in a sliver of width about (2/3)·4^{−k} below t_k. Nothing I tried bounds the 1/2 walk's remainders at every skip.

## 2. Friction with the MCP surface (new this session)

1. **The skeleton comment rule is learned only from a refusal.**
   Call: `write precheck_submission {node_id:"spec-a70fcca4--h4--h2", artifact_type:"partial", bundle:{…/attempts/20261124T231000Z-t1125-257-partial.lean: <two sorry'd haves, no comments>}}`.
   Answer: `400 partial-unlabelled`, "a partial names its approach, a licence and each hole's label and claim in its comments (D-12 v3.44; the guide's Skeletonization section) …", with a `details.missing[]` list per hole.
   - The refusal itself is excellent: it names every missing line, and the line number of each.
   - But nothing earlier says so. The descriptions of `precheck_submission` and `submit_proof` don't mention the `-- approach:`, `-- licence:`, `-- label:` and `-- claim:` lines. Nor does `search {query:"submit a skeleton proof with holes"}`.
   - `check_lean` already flags the text as a skeleton (`sorry-present`: "a skeleton is submitted as a partial"), but it does not lint the missing comments either. So the rule costs one precheck round trip.
2. **There is no way to see a hole's closed type before a full precheck.**
   - In v1 and v2 the hole `h_tail_irr` sat after `intro r h0 hstep`. Its closed type came back as `∀ (r : ℕ → ℝ), r 0 = 1/2 → (walk) → ∀ M, Irrational (…)`, even though the walk hypotheses are unused. The gate lists an `unused-binder` hazard checker, but it raised no finding here.
   - Its `expected_witness` was a whole walk existence statement, `∃ r M, r 0 = 1/2 ∧ …`.
   - I only learned this from `get_precheck(...).holes[].closed_type`, about 3.5 minutes per round.
   - On the other hand, an earlier *hole* in scope is correctly left out of a later hole's closed type: in v2, `h_tail_irr` was in scope for `h_skipgap` and did not appear. That is good, but undocumented.
   - A `check_lean` mode that prints `holes[].closed_type` (it already has the goals as "unsolved goals at sorry") would save whole precheck cycles.
3. **`check_lean` reports `okay` differently by mode for the same sorry'd skeleton.**
   - `mode:"verify"` gave `"okay": false` with `sorry-reported` and `context-restated`.
   - `mode:"check"` on the same proof body gave `"okay": true`, with lint `sorry-present`.
   - Neither answer says which `okay` a skeleton should aim for.
4. **`get_node … include: []` can still be about 90k characters.**
   - `read get_node {node_id:"spec-a70fcca4--h4--h1--h1--h1", include: []}` → the client refused: "result (91,002 characters) exceeds maximum allowed tokens".
   - The same happened for `--h4--h1--h2--h1` (93,041 characters).
   - `include: []` is documented as "the Lean, the context, the claims, the lemmas, the label and the open submissions alone". Something in that set, probably long attempt records or review questions inlined in the context, is huge. There is no way to ask for only the statement.
5. **`list_frontier` is stale about a merged proof.**
   - `read list_frontier {filters:{target_id:"erdos-257"}}` at 23:07Z (rendered_from 2e5927f3…) still lists `spec-9ab4bdf6` as `status: "speculative"`, `needs: "proof"`, `claimable: true`.
   - Its proof, PR #2031, merged at 22:59Z, so the frontier invites a second proof of a proved node.
6. **The attestation still drops the declared automation.** This is the same as last session's item 4, and still true.
   - Every `get_precheck` in this session echoes `automation {method:"agent", models:["claude-opus-5-5"], framework:"claude-code"}` at the top level.
   - Inside the signed `attestation`, the fields read `"automation": null`, `"model_and_tooling": "undeclared"` and `"tooling": {"harness": null, "model": null}`.
7. **Prechecks are slow, with no wait primitive.**
   - One job took about 3.5 minutes. With two jobs in flight, one took about 6 minutes: 01M87XG4… was created at 23:15:48 and done at 23:19:35.
   - I polled `get_precheck` by hand more than 15 times. A `wait_seconds` argument, or a long-poll, would remove that.
8. **`search` with a query returns whole schemas.** `search {query:"submit a skeleton proof with holes", limit:4}` returned four full input schemas, about 12k characters, when I wanted names and ranks. A brief mode would help; the no-argument listing has no descriptions at all.
9. **Nothing points to a proved node that a hole restates before a precheck.**
   - I spent a precheck cycle (v4) to learn, through `holes[].restates: "variant-2f5236aa"`, that Erdős 1948 is already a proved node.
   - No read operation answers "is this statement already a node?". Neither `search` nor `get_node` takes a statement or hash lookup, and `list_frontier` lists only open nodes.
   - A cheap "find node by statement" read, or `check_lean` reporting `restates`, would have let me import the proof from the start.
   - Related: the use-line rule (`import Nodes.«id».Proof`) is in the operation descriptions, which is good. But nothing says that `check_lean` inlines the used proof *as its statement with sorry*. So `check_lean` reports `Opn.erdos_257_all_naturals` as "declaration uses sorry" and lists it under `failed_declarations`, though it is proved. It looks like a failure and isn't one.
10. **`list_sufficient_sets` is where the structure lives, but I found it late.**
    - The equivalence `--h4--h2` ⟺ `--h4` (given variant-2f5236aa) was stated only in route @2's `approach` string, and in a postmortem's `detail`, which `get_node` truncates (`"shortened":["detail"]`).
    - I found it after writing three skeletons. A hole node's `get_node` could list "routes of the parent that pass through this node", with their approaches.
11. **`submit_proof`'s receipt explains a restated hole becoming a *lemma*, not a dependency, only after submission.**
    - The receipt's `holes_note` says: "makes that node a lemma of this node … this node never waits on it".
    - That changes what the partial achieves: the node gets a lemma, not a closing route. I would have wanted to know it at precheck time; the precheck diagnostic `artifact-reduction` says nothing about lemma versus dependency.
12. **Precheck's `artifact-reduction` versus the submitted `artifact_type: "partial"`.**
    - The v6 precheck labelled the kernel-replay step `code: "artifact-reduction"`, with `details.kind: "partial"`.
    - `artifact_type` has a separate `reduction` value. I guessed that `partial` was right, since that is what I prechecked as; `submit_proof` accepted it.
    - Nothing says when a one-hole partial whose hole restates an existing node should be filed as `reduction` instead.

13. **`get_submission`'s `pull_request` block was stale while it said fresh.** This is the same issue as last session's item 5, and still present.
    - At 23:31:17 and again at 23:32:40, `pull_request.read_at` stayed `2026-11-24T23:30:37Z`, with `runs: []` and `"stale": false`.
    - The `queue.read_at` field did advance between those calls.
14. **An explainer for a just-merged partial is refused until the products land.** The refusal is clear.
    - Call: `write submit_gloss {subject:{kind:"proof", node_id:"spec-a70fcca4--h4--h2", proof:"11ed076e…"}, dry_run:true, …}`.
    - Answer: `409 products-pending`, "… its outline … is not yet in the graph … usually about fourteen minutes after the merge … Retry shortly", with `retry_after_s: 300`.
    - This is good: it named the artifact, confirmed that my locally computed SHA-256 was the right proof hash, and said that words naming no `{steps: …}` could be filed now.
    - It is an improvement over last session's `explainer-proof-unknown`.
15. **`release_claim`'s argument name was a guess.** I used `{claim_id: …}` without reading its schema, and it was accepted. Fine, but `list_my_claims` returns `id`, not `claim_id`.

## 3. Process
- Claim 01M87X23X8N9J60DS2B1R5WGKF on `spec-a70fcca4--h4--h2`: taken 23:08Z, released 23:36:34Z after the merge.
- No token written anywhere.

## 4. End state
- **PR #2042 (partial on `spec-a70fcca4--h4--h2`): merged 23:35:03Z.**
  - Merge commit 1201e8ae; gate success, `gate_report {ok: true}`.
  - The submission then showed `waiting_on: "products"` and `attestation-pending`.
  - One hole, `hgap`, which restates `spec-a70fcca4--h4--h1`. It becomes a lemma of `--h4--h2`.
  - Precheck job 01M87Y1SJR0BMXMYX6PQR2RP6H: verdict pass, footprint `[variant-2f5236aa]`.
  - Lean hash 11ed076e20c8c5435c95014540cbcad93c4e7f01f5b1918ad98c060905e4ec9d.
- Explainer for #2042: **PR #2043**, filed 23:50Z and open at the end of the session.
  - Two dry runs (23:38Z and 23:44Z) were refused `409 products-pending`, so products took roughly 9 to 15 minutes after the merge.
- Not submitted: the prechecked skeleton versions v1–v4. Their attestations are on jobs 01M87X56…, 01M87X9F…, 01M87XG4… and 01M87XMG…; all passed.
- No proof of an open node. The open content of this branch is unchanged: `--h4--h1` and its window rungs.
