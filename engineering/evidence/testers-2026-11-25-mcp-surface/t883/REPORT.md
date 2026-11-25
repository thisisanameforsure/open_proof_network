# REPORT — t1125-883 on erdos-883 (Erdős 883, part i)

Harness: claude-code · Model: Claude Opus 5.5 (claude-opus-5-5) · Window 22:41Z–23:41Z

## Mathematics

### Statement fidelity (no defect)
I compared the Lean statement with erdosproblems.com/883 part i:
- `n / 2 + n / 3 - n / 6` is ⌊n/2⌋+⌊n/3⌋−⌊n/6⌋, and ℕ-subtraction cannot truncate.
- `l ≤ n / 3 + 1` is equivalent to l ≤ n/3+1 for an integer l.
- `Odd l → 3 ≤ l` covers every odd cycle length.
- `coprimeGraph = fromRel Nat.Coprime` puts an edge between distinct coprime integers. It is induced on A, and `oddCycleLengths` uses Mathlib's `IsCycle`.
- An exhaustive Python search (|A| = T(n)+1 suffices, because supersets keep their cycles) found no counterexample for n ≤ 22.

I filed no defect claim or revision request because the formalization is faithful.

### Submitted
- **PR #2027**, statement gloss (merged): LaTeX statement, Lean conventions, and why the bound is sharp at l = 3.
- **PR #2029**, witness gloss (merged).
- **PR #2030**, informal annex (merged): fidelity review, the n ≤ 22 finite check, sharpness, and the split at l = 3.
- **PR #2041**, partial proof of erdos-883 with one hole: precheck job `01M87XB8W8JDXKBWTCNBTRC5AX` passed, submission `01M87XRTF87CPVAYVRE69KP9ET`. At 23:20Z it was open, first in queue and waiting on the gate. The hole h_long is planned as the new node `erdos-883--h1`. The file is `targets/erdos-883/nodes/erdos-883/attempts/20261124T225600Z-t1125-883-partial.lean`.
  - **The case l = 3 is fully proved in Lean.** If |A| > ⌊n/2⌋+⌊n/3⌋−⌊n/6⌋ and n ≥ 6, then A contains three distinct pairwise-coprime elements, so G(A) has a triangle (`erdos883_tri_mem` builds the 3-cycle walk).
  - The proof is elementary and new to this graph:
    - `erdos883_cop`: gcd(a, a+d) = 1 when d = 1; when d ∈ {2, 4} and a is odd; and when d = 3 and 3 ∤ a.
    - `erdos883_window`: any 5 elements of {6k+2, …, 6k+7} contain a pairwise-coprime triple, using the triples {3,4,5}, {5,6,7} and {3,4,7} at offset 6k.
    - `erdos883_blocks`: induction on q gives |S| ≤ 4q for a triangle-free S ⊆ [2, 6q+1].
    - `erdos883_no_one`: when 1 ∉ A, a case split on the tail n − (6q+1) ∈ {0, …, 5} gives the exact bound ⌊n/2⌋+⌊n/3⌋−⌊n/6⌋.
    - `erdos883_pairs`: when 1 ∈ A, A∖{1} has no coprime pair. Consecutive integers are coprime, so pairing {2j+2, 2j+3} gives |A∖{1}| ≤ ⌊n/2⌋, and 1 + ⌊n/2⌋ ≤ T(n) for n ≥ 3.
  - The assembly splits an odd l ≥ 3 into l = 3 or l ≥ 5.

### Not submitted on purpose
My first precheck (job `01M87VV6SGPJCXVHHR8YNXEQ75`) **passed**, but its hole `h_tri` lacked `6 ≤ n` and is false at n = 1, A = {1}. I did not submit it. The fixed 2-hole version was blocked by `products-pending`, and by the time the block lifted I had proved h_tri, so the 1-hole version replaced it.

### Left open
- **h_long** (planned as a new node): for odd l with 5 ≤ l ≤ ⌊n/3⌋+1 and |A| > T(n), G(A) has an l-cycle. This is the real content of Erdős–Sárközy (1997). The brute force confirms it for n ≤ 22, where it is non-vacuous only for n ≥ 12.
- The words for the defs files (list_words_needed shows nine definitions without glosses). I held them back deliberately, because each words merge re-triggers `products-pending` on the node.

### Local artifacts
The scratchpad of this session holds `bf.py` (the brute force), `window.lean`, `tri2.lean` and `theorem_tail.lean`, which together are the submitted helper lemmas and assembly. The submitted file itself is in PR #2041.

### Evidence
- The fast check of the window lemma returned `okay:true` with no errors.
- The fast check of the full triangle chain had one error, which I fixed (`<;> omega` in `erdos883_split`).
- The authoritative precheck passed every step: toolchain, paths, kernel-replay, axioms, hazards, witness and deps.

## MCP surface frictions

1. **The argument name differs between `get_target` and `get_node`, and I had to guess both.** A bare `search` lists operation names but no arguments, so my first call guessed.
   - Call: `read get_target {"id": "erdos-883"}`
   - Answer: `{"error":"arguments-invalid","message":"'target_id' is a required property; target_id: A target's id, as list_targets names it.; not an argument of get_target: id"}`
   - Then I sent `target_id` to `get_node`, and the opposite happened. Call: `read get_node {"target_id": "erdos-883", "node_id": "erdos-883"}`
   - Answer: `{"error":"arguments-invalid","message":"Additional properties are not allowed ('target_id' was unexpected); not an argument of get_node: target_id"}`
   - Both messages said what to do, which is good. But `claim_node` accepts an optional `target_id` and `get_node` refuses one, which is inconsistent.
   - `list_frontier` refuses it too. Call: `read list_frontier {"target_id": "erdos-883"}` → `{"error":"arguments-invalid","message":"Additional properties are not allowed ('target_id' was unexpected); not an argument of list_frontier: target_id"}`. Nothing said how to scope the frontier to one target.

2. **`search` has no operation named for decomposition or skeletons.** Call: `search {"query": "submit a decomposition into lemmas / holes"}` returned submit_proof, submit_informal_annex, submit_candidate, submit_postmortem and submit_gloss. The partial-with-holes format (the path `attempts/<ts>-<pseudonym>-partial.lean`, the `-- approach:` / `-- licence:` / `-- label:` / `-- claim:` comments, and holes as `have … := sorry`) is not in any schema. I had to fetch AGENTS.md, a 206 KB page, to learn it. The `<ts>` format was a guess: I used `20261124T224631Z`, and it passed.

3. **`check_lean` with `node_id` inlines defs in a way that breaks compilation, so `okay` is always false.** Call: `write check_lean {"node_id": "erdos-883", "mode": "check", "content": "import Mathlib\nimport Defs.CombinatoricsSimpleGraphCircumference\nimport Defs.Local\n…"}`
   - Answer: `okay:false`, with 48 `failed_declarations`, nearly all `SimpleGraph.MilnorK.*`.
   - Errors included `Unknown identifier 'gcd_insert'` and `Function expected at ι`.
   - Cause: the server inlines **all nine** Defs files, even the ones not imported. `CombinatoricsSimpleGraphColoringVertex.lean` opens `namespace SimpleGraph` and never closes it. Every later def (MilnorK, Finset.Coprime) and my own lemma then land in `SimpleGraph.*`, where `ι` resolves to a variable.
   - The response also carried the lint `imports-differ`, so to avoid that lint I would need all nine imports, which brings in the breakage. The fast check is unusable for this target with `node_id`. My workaround was `target_id` plus `import Mathlib` only, for helper lemmas that need no defs; that returned `okay:true`.

4. **Large results overflow the MCP client.** The `check_lean` response above (61,728 chars) and `list_error_codes` (136,281 chars) both exceeded the tool-result limit and were saved to disk. Most of the size is `result.content` echoing back the whole submitted file plus the inlined defs. An option to omit the echo, or a `code` filter on list_error_codes, would help.

5. **The precheck accepted a hole that is false.** My first partial had the hole `h_tri : ∀ n A, A ⊆ Icc 1 n → n/2+n/3-n/6 < A.card → ∃ three distinct pairwise-coprime elements`. It is false at n = 1, A = {1}. Job `01M87VV6SGPJCXVHHR8YNXEQ75` returned `verdict: pass` and planned the hole as new node `erdos-883--h1`. Its `expected_witness` only shows the hypotheses can be satisfied. Nothing warned that the hole might be false, and a merge would have put a false node on the frontier. I caught it myself and did not submit that job. A quick small-case evaluation of decidable holes would catch this class of mistake.

6. **`products-pending` blocks prechecks for several minutes after a words merge.** My gloss and annex PRs merged (#2027, #2029, #2030), and then every precheck on the node was refused.
   - Call: `write precheck_submission {"node_id":"erdos-883","artifact_type":"partial",…}`
   - Answer: `409 {"error":"products-pending","message":"graph commit 9656f28f1c80… changed erdos-883's nodes after b6c40d00317a…, the commit that wrote its products, so the holes this bundle would make cannot yet be planned against every node they might restate. It waits for that merge's products. Retry shortly.","details":{…"retry_after_s":300}}`
   - `list_error_codes` explains it as "The node merged a moment ago". The node itself had not merged; only words attached to it had.
   - The lesson for contributors is to submit words *after* the proof precheck, not while it is pending. The task brief recommends the opposite: "while a precheck … is pending, write words".

7. **`products-pending` lasted about 22 minutes, not "shortly".** Prechecks were refused at 22:51, 22:56, 23:01 and 23:06Z, each with `retry_after_s: 300` and the same commits (`9656f28f` vs `b6c40d00`). The next try was accepted at 23:13Z, at graph `b6fda248`. Nothing on the surface shows whether the render is queued or progressing, so all I could do was resend a 25 KB bundle every few minutes. A read operation for products status, or a precheck that queues behind the render instead of refusing, would fix this.

8. **A refusal on `submit_proof` pointed away from the real problem.** As a test, I sent `submit_proof` with a passing `precheck_job_id` and a placeholder bundle (`"…partial.lean": "PLACEHOLDER"`).
   - Answer: `400 partial-unlabelled … "missing":[{"code":"approach",…},{"code":"licence",…}]`
   - The real problem is that the bundle does not match the prechecked digest, but the refusal speaks only of comment lines.
   - The schema also does not say whether the bundle is required when a precheck id is given. It is; I had to resend the full 25 KB file.

9. **A step code changed between the two prechecks.** Step 4 reported `artifact-partial` on the 2-hole precheck but `artifact-reduction` on the 1-hole one, while `kind` stayed `partial`. I submitted with `artifact_type: "partial"`, as prechecked, and it was accepted. Nothing said whether `reduction` would have been the right type.

10. **`list_words_needed` is stale.** At 22:58Z it still listed `Witness.lean` as `reason: "no-gloss"`, after my witness gloss PR #2029 merged at 22:51Z.

11. **`release_claim`'s argument name was a guess.** I sent `{"claim_id": …}` without fetching the schema, and it worked. A bare `search` gives no argument names, so every first call to a new operation is either a guess or an extra `search` round trip.

12. **The approval layer refused my shell commands.** This is harness friction, not the MCP surface. Shell redirects into the working directory, `sed -i`, and `python3 -c` with backslashes were refused, so LOG.md was kept with the Edit tool.
