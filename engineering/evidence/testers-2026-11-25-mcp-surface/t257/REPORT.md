# REPORT — t1125-257 on erdos-257 (22:41Z–23:41Z)

## 1. Mathematics

### The state of the target, and why I did not move the root
`list_sufficient_sets {target_id: "erdos-257"}` gives two sets that would **prove** the root:

- `s-fb6cd66200` needs `erdos-257--h2--h1` ("a rational's greedy set is finite or co-finite").
  For r = 1/2 the greedy set is infinite (no finite subsum is 1/2, `spec-a70fcca4--h2`). Erdős 1948 rules out
  the co-finite case unless the walk stalls with every later step taken. So the hole, at r = 1/2, says the 1/2 walk
  eventually takes every step and stalls. The route's own approach text says it is expected false, and
  `spec-a70fcca4--h4--h2` (open) would refute it. This is not a live way to prove the root.
- `s-1f9c3f315f` needs `erdos-257--h18` ("every other infinite set", i.e. the whole problem) and
  `variant-6b364d2b--h1--h1` (Tao–Teräväinen §§5.6–5.14, κ₂–κ₅ for primes). I read the full statement.
  With S1 = S2 = ∅ and a one-element Ns, most conjuncts become trivial: the moments, the S2 variance, and the exp bound
  once M is large. Two conjuncts carry the analytic content of TT §5:
  - Equidistribution of m(n, ε) mod each P_ε forces |Ns| ≳ P_ε, so Ns is a CRT box.
  - The Mertens window (2^K·T ≤ log log R − log log w with Σ_{p∈(w,R]∖S1} 1/p ≤ 1) forces S1 to carry nearly all the
    prime mass in (w, R].

  Not feasible in an hour.

Every other open hole (the greedy-walk windows, the carries, the repair walk, the calm points) is on the **refutes**
side (`spec-a70fcca4-v2`, `variant-cce9b284`), and each one is open mathematics: either Dickson-type prime
constellations or the skips of the 1/2 walk. **Nothing I could close in 60 minutes moves the root, and I did not
move it.**

### What I proved: `spec-9ab4bdf6` (Opn.erdos_257_calm_point_third_position) — PR #2031
For m ≥ 1092 with m+1 prime: either #{a : 20 < a < m, a | m+3} ≤ 4, or G(m) > 99/100.

The proof needs only the first four terms of G:
- m+1 is an odd prime, so m is even.
- If m+3 has five such divisors, they give 5/8.
- If m = 4j+2, then (m+2)/2 and (m+2)/4 give 2/4, for a total of 9/8.
- If m = 4j, then (m+2)/2 gives 1/4, and (m+4)/2 and (m+4)/4 give 2/16, for a total of 1.

This proves the "c_m(m+3) ≤ 4" step of condition N1 in annex `eaaf51ac…` on `variant-cce9b284--h6`. That annex
used an exact computation over all 27720 residues; this proof does not need one. Together with the merged
`spec-23231427`, every calm point m ≥ 1092 has at most four divisors of m+3 in (20, m).

The node is a speculative crux proposed for `variant-cce9b284--h6`, on the refutes side. It sharpens the known
barrier for that hole and does not change the root's status.

Evidence:
- check_lean (mode verify): `okay: true`, no lint, no warnings.
- precheck job `01M87VSQXGEKHQ6128B84RGW10`: verdict pass (steps 1, 2 and 4–8; kernel replay, axioms, hazards and
  witness all pass).
- submit_proof gave PR #2031. Its gate run succeeded (`gate_report {ok: true}`), then the PR was rebased and gated
  again. Merge state at the end of the session: SEE §4.

### Words (all filed through `submit_gloss`)
| PR | subject | state |
|---|---|---|
| #2026 | gloss, `spec-9ab4bdf6` statement | merged |
| #2028 | gloss, `spec-2690fb43` statement (proved barrier "calm points ⇒ prime pairs") | merged |
| #2032 | explainer, `spec-2690fb43` proof | merged |
| #2033 | explainer, `variant-cce9b284--h13` proof (parity: no finite set sums to 2^-j) | merged |
| #2034 | explainer, `variant-cce9b284--h4` proof (walk count ≤ walk-free G_20) | merged |
| #2035 | explainer, `variant-cce9b284--h8` proof | merged |
| #2036 | explainer, `variant-cce9b284--h10` proof | merged |
| #2037 | explainer, `variant-cce9b284--h7` proof (no stall ⇒ chosen set sums to x) | SEE §4 |
| #2038 | explainer, `variant-cce9b284--h3` proof (binary digits of 1/(2^a−1); stall ⇒ W > 99/100) | SEE §4 |
| #2039 | explainer, `variant-cce9b284--h5` proof (integer interval walk to 1092, kernel-decided) | SEE §4 |

With these, every merged proof on erdos-257 that `list_words_needed` listed as lacking an explainer has one filed.

### What is left open
Unchanged by this session:
- Root-proving holes: `erdos-257--h18` and `variant-6b364d2b--h1--h1`.
- Refutes side:
  - `variant-cce9b284--h6`, which implies the open prime-pair statement `spec-001a7622`.
  - `variant-cce9b284--h11`, `--h2--h1` and `--h2--h4`.
  - `spec-a70fcca4--h4--h2` and its window rungs (`--h1--h1--h1`, `--h1--h2--h1`).
  - `spec-a70fcca4-v2--h3`.
- Elsewhere: `variant-5274cf38--h1--h1` and `--h2`; their parent is already proved, so they do not move anything.

## 2. Friction with the MCP surface

1. **First call guessed the argument name.**
   `read {"operation":"list_sufficient_sets","arguments":{"target":"erdos-257"}}` →
   `{"error":"arguments-invalid","message":"'target_id' is a required property; ... not an argument of list_sufficient_sets: target"}`.
   The message was clear and fixed it in one retry. But `search` with no arguments lists operations without their
   schemas, so the first call to any operation is a guess unless I first call search again with `operations: [...]`.

2. **Lint code not documented anywhere.**
   `check_lean {mode:"verify"}` with private helper lemmas placed between the imports and the theorem returned
   `okay: true` plus `lint: [{"code":"header-diverges","message":"Proof.lean diverges from Statement.lean at line 4 (header or signature): the gate takes a proof as the statement with its sorry replaced (F00-R19) and refuses this at step 2", ...}]`.
   - `list_error_codes {prefix:"header"}` → `{"count":0,"codes":[]}`, and a full `list_error_codes` has no `header-diverges`.
   - The merged proof of `spec-2690fb43` (read via `get_node`) has exactly that layout: private defs before the
     docstring and theorem. So either the rule changed after it merged, or it depends on something the message does
     not say. I guessed the fix (move the helpers inside the proof as `have`s), and it worked.
   - The lint does not say whether top-level helpers *after* the imports but *before* the docstring are ever allowed.

3. **`list_error_codes` with no prefix is about 136k characters** and overflowed the client's tool-result limit.
   A default page or a `code=` exact lookup would help; `prefix` exists but I had to know the prefix first.

4. **The attestation drops the declared automation.**
   I passed `automation {method:"agent", models:["claude-opus-5-5"], framework:"claude-code", ...}` to
   precheck_submission. `get_precheck` echoes it at the top level, but the signed `attestation` inside has
   `"automation": null`, `"model_and_tooling": "undeclared"` and `"tooling": {"harness": null, "model": null}`.
   It is not clear whether that matters for credit. (submit_proof took `automation` and `tooling` again.)

5. **`get_submission` reports a stale pull-request state as fresh.**
   - At about 22:55:42 the `pull_request` block showed the gate `completed/success`, `waiting_on: "branch-update"` and
     `gate_report {ok: true}`.
   - The next call showed `read_at: 22:55:11`: an *older* read, with the gate `in_progress`, `gate_report: null` and
     `"stale": false`.
   - Earlier, `pull_request.read_at` stayed at 22:52:06 across calls while `stale: false`.

   The `stale` flag did not reflect any of this.

6. **The explainer section format is learned only from a refusal.**
   `submit_gloss {subject:{kind:"proof",...}, dry_run:true, text:"**Theorem.** ..."}` →
   `400 explainer-invalid: "an explainer's body is sections under level-2 headings (## ...) (F20-R2; explainer/v1)"`.
   The message is clear, but the `submit_gloss` description and the `text` argument's description only say how a
   *gloss* opens (LaTeX first). They say nothing about `##` sections for explainers.

7. **Search ranking.**
   - `search {query:"which nodes would prove the root"}` ranked `get_node` and `claim_node` above
     `list_sufficient_sets`, the operation that answers it, which came third.
   - `search {query:"what does an error code mean"}` ranked `list_error_codes` first (good).

8. **Waiting on a precheck.** A precheck took about 5 minutes. There is no blocking or long-poll form of
   `get_precheck`, so I polled it about 8 times by hand.

9. **Minor.** `claim_node` returned `created: 2026-11-24T22:43:30Z` while the session date is 2026-11-25. My local
   clock and the server agree on the time of day, so this is probably a date or timezone mismatch in the harness
   rather than in the service. `submit_proof` requires `automation` while `tooling` is a separate, optional,
   older-style field (D-23); I filled both, guessing.

10. **A partial's Lean cannot be read through the MCP.**
    `list_words_needed {target_id:"erdos-257", kind:"partial"}` lists three partials needing explainers, e.g.
    `targets/erdos-257/nodes/variant-cce9b284/attempts/20261113T133000Z-fable-1113-e257-partial.lean`.
    But `get_node {node_id:"variant-cce9b284", include:[]}` gives only
    `attempts.assemblies[] {bytes, hash, path}`, and `files` holds just Statement/Context/Witness/Proof. No read
    operation returns an attempt file's text. So an MCP-only contributor cannot write those explainers without
    guessing, and I skipped them.

11. **A merged gloss is not reflected in `get_node`.**
    My statement gloss for `spec-9ab4bdf6` (PR #2026, with `label: "Third position of a calm point: m+3 has few divisors"`)
    merged at 22:48Z. At 22:59Z, `get_node {node_id:"spec-9ab4bdf6"}` still returned `"label":"spec-9ab4bdf6"`,
    `"label_source":"id"`, `"claim":null` (`rendered_from` c25bd15…). Either the context is rebuilt lazily or the
    label is not picked up; the response does not say which.

12. **Two wait states with no hint.** `get_submission` for #2031 moved through `waiting_on: "gate"`, then
    `"branch-update"` (mergeable_state `behind`), then `"gate"` again, then `"merge"`, all with the same `head_sha`
    and the same gate run id. Nothing says how long `merge` usually takes or what it is waiting for. At 22:59:07 it
    was back to `waiting_on: "branch-update"`, `mergeable_state: "behind"`. Main kept moving, partly because my own
    explainer PRs merged in the words lane. So a contributor who follows the instruction "write words while a merge
    is pending" delays their own proof's merge. The two lanes are described as independent, but they share main.

13. **Right after a merge, the words surfaces lag.** After #2031 merged (22:59:10Z, `waiting_on: "products"`):
    - `list_words_needed {kind:"proof"}` (read_at 2af01d84) still listed the 8 proofs whose explainers had already
      merged (#2032–#2038), and did not list `spec-9ab4bdf6`.
    - `submit_gloss {subject:{kind:"proof", node_id:"spec-9ab4bdf6", proof:"c4379e77…"}, dry_run:true}`, using the
      attestation's `artifact_hash` (my guess for the proof hash), gave
      `400 explainer-proof-unknown: "... which is not a merged proof artifact of spec-9ab4bdf6 ...; the node's are: none"`.

    So there is a window after merge in which no surface gives the proof hash an explainer needs, and nothing says
    when the window closes. It is also undocumented whether the attestation's `artifact_hash` is that hash.

## 3. Process notes
- The claim on `spec-9ab4bdf6` was taken at 22:43Z (ttl 2h). SEE §4 for release.
- No token was written to any file.

## 4. End-of-session state (23:05Z)
- **PR #2031 (proof of `spec-9ab4bdf6`): merged at 22:59:10Z** (merge commit 1ec2b069). At 23:05 the submission
  still said `waiting_on: "products"` and `attestation-pending`, and `get_node` still showed the node as
  `speculative` with `proof.present: false`, although `Proof.lean` is served.
- PRs #2026, #2028 and #2032–#2039: merged.
- PR #2040 (explainer for my own proof): open, in the gate.
  - The attestation's `artifact_hash` (c4379e77…) is the proof hash `submit_gloss` wants. That worked only once
    the post-merge products had landed, about 5 minutes after the merge (friction item 13).
- Claim `01M87VMZJGHBCT2AGGNZ924TC2` on `spec-9ab4bdf6`: released at 23:04:40Z.
- Totals: 1 proof merged, 2 glosses and 8 explainers merged, 1 explainer pending.
  - Not attempted: explainers for the 3 partials, whose Lean text I could not read through the MCP.
- I stopped at 23:05Z, before the 23:41Z deadline, because nothing within reach would move the root and every
  file left without words is either unreadable through the MCP or already has a pending PR.
