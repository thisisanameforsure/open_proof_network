# Calibration run — erdos-1050 (F15-T14c) — agent log

Target: `erdos-1050` (graded easy). Statement: `Irrational (∑' n : ℕ, (1 : ℝ) / ((2 : ℝ) ^ (n + 1) - 3))`.
Agent: Fable 5.1 (Claude Code), unattended, started 2026-09-17 (wall clock start of this file).
Common brief: `engineering/session-notes/2026-09-17-calibration-run-handoff.md`.

Rules I am under: never commit/push/merge/close anything on the graph; never touch its main
working tree; on the network repo write only this file and scratch files
(scratchpad: `/private/tmp/claude-501/-Users-mikehiggins-Desktop-repos-open-proof-network/835932f5-156f-4eb6-a7d1-1ab6456274b0/scratchpad`).
No Mathlib on the laptop; never pull the Mathlib docker image. Iterate on `POST /check`.

## State (keep current)

- **State (final, 14:27Z): PR open — gate GREEN, step 9 waiting for a human review.** Graph
  **PR #78** carries the one-hole partial (skeleton): the gate job `gate (steps 1, 2 and 4-8 in
  the sandbox)` is **SUCCESS** (run `35233188330`, job `105242323514`: classification
  `mode: partial`, verdict `pass`, every step pass, 1 hole `borwein`, precheck
  `01M2QVS0GG8CR7JZ5T80N8V8C4` recognised against graph commit `1f9fb28`). The job
  `step 9 (a non-author approving review)` is **FAILURE** by design: erdos-1050's fidelity is
  `mechanical-only`, so `targets/index.json` says `step9: review`, and the job's message is
  "step 9: this node's root has no fidelity certificate or registry provenance, so a non-author
  approving review is required before merge (D-4 v3.11 …). Approving re-runs this check; the
  build above is not repeated." `mergeStateStatus: BLOCKED` until that approval. The annex is
  graph **PR #76** (gate SUCCESS, CLEAN). I merged, closed and pushed nothing. A full proof was
  judged out of reach in the box (Borwein's Padé argument; steps 6 and 9); the partial is the
  honest artifact, and the network's outcome for this target after the lead's merges is
  *open, blocked on one hole `erdos-1050--h1`*, not `resolved`.
- **Check ids:** network `/check` (dead, stale AXLE env): `01M2QV4M5GDVSK91G7R0E6366D` (404
  target-unknown), `01M2QV6GQ0YZBS53HXZ2DNZ20M` (user_error unknown environment),
  `01M2QVJ4S8JRCF24E9M82TZV98` (verify-mode lint on draft 1: `sorry-present` only). Direct AXLE
  `lean-4.33.1` requests: `0b243356-21d8-475e-93b7-456a2307cb6c` (statement baseline),
  `c2aa50e1-3c72-4635-a959-37e8a0d6ad3d` (draft 1, two unknown identifiers),
  `3ded8686-43aa-4e4c-9481-8a8592f4cd5a` / `985477e4-1b4f-42b0-94d8-d684835c3de7` (drafts 2A/2B
  pass), `07ec4845-6634-4c34-a4af-76c21f7ccc28` (2C fails), `3009e41a-e3a2-4d3e-a9b4-ecf0ad8366b6`
  (final partial with the annex citation: `okay: true`, only the sorry warning).
- **Precheck ids:** tutorial (anonymous, for the token) `01M2QVKHPRPXS6SVJ684EHJ8KS` → pass;
  owned partial precheck `01M2QVS0GG8CR7JZ5T80N8V8C4` (created 14:19:22Z, done 14:22:46Z,
  `authenticated: true`) → **verdict pass**, signed by `service`, runner `hosted`; steps:
  1 toolchain pass (`mathlib-pinned`: Mathlib 0df444a360ea resolved from the pinned checkout,
  8 packages); 2 paths pass (`partial-submission`: attempts/20260917T141921Z-calib-1050-fable-partial.lean,
  D-12 #5); 4 kernel-replay pass (`artifact-reduction`: "partial: Opn.erdos_1050 declares
  Irrational (∑' (n : ℕ), 1 / (2 ^ (n + 1) - 3)); 1 hole(s)", holes `["borwein"]`); 5 axioms
  pass; 6 hazards pass (`hazards-acknowledged`, the root's div-zero acknowledgement); 7 witness
  pass; 8 deps pass. Saved: scratch `precheck-result-direct.json`.
- **PR numbers:** graph **#76** = the annex (`annex/ebfc846b7b9ca01cf3880bbde14e6a4909e741934a08f0b4d43f8aa3b2405cb2.md`,
  append id `01M2QVRVM8HBKA2KTT3TRTNJCC`; gate SUCCESS, `mergeStateStatus CLEAN` at 14:20Z).
  Graph **#78** = the partial (submission id `01M2QVZJF8NSB70424HVM5VYZX`, opened 14:23:0xZ by
  the App for pseudonym `calib-1050-fable`, bundle
  `targets/erdos-1050/nodes/erdos-1050/attempts/20260917T141921Z-calib-1050-fable-partial.lean`).
  Merge order for the lead: #76 first (wait for its bot commit), then #78.
- **Token:** minted 14:18:44Z, identity id `01M2QVQVD0PVJRVE8GMRB7W0J0`, pseudonym
  `calib-1050-fable`, proof kind `tutorial`; lives only in scratch `token.json` (never logged).
  A successor on a fresh machine needs a new token (guide §"Getting a token").

## Facts established

- Live node `targets/erdos-1050/nodes/erdos-1050/Statement.lean` on `origin/main` is byte-identical
  in content to `engineering/onramp/calibration/erdos-1050/Statement.lean`: header = Apache
  licence block, `import Mathlib`, one module doc comment, then
  `theorem Opn.erdos_1050 : Irrational (∑' n : ℕ, (1 : ℝ) / ((2 : ℝ) ^ (n + 1) - 3)) := by sorry`.
  No `open` lines. Witness is `True`.
- Registry file `engineering/onramp/calibration/upstream/1050.lean` cites an external Lean 4 proof:
  `gotrevor/lean-gallery`, `LeanGallery/NumberTheory/Erdos1050/Statement.lean` (Trevor Morris with
  Claude Code and Harmonic's Aristotle). Prior art for the record (R14 c): Borwein 1991 (J. Number
  Theory 37, 253–259), Borwein 1992 (Math. Proc. Camb. Phil. Soc. 112, 141–146).

- Live node `META.yaml`: `schema: meta/v2`, `status: ready`, `deps: []`, `origin: authored`,
  `statement-hash: 679c2dd5b1400f16ae52bf3dcf9a26574e89e793eedd7fe5ff2e98a9fa7bd6c2`, one
  acknowledged hazard (`div-zero` at `1 / (2 ^ (n + 1) - 3)`). `Context.lean` declares no deps.
  No `CONTEXT.json` on `origin/main` (the api derives it). Gate-spec: network `0401858`,
  Mathlib `0df444a3`, Lean `v4.33.1`, image `gate@sha256:0a300f39…`, step-3 cap 600 s wallclock.
- Step-2 rule (`gate/opn_gate/paths.py::check_proof_is_statement`, `layout.py::Statement`):
  `prefix` is the statement text up to and including the `:=` that opens the sorry body; the
  proof file must start with it byte for byte, and `suffix` (text after `sorry`) must end it.
  So **no declarations before the theorem**: every helper is a `have` inside the proof body.
  Proof.lean = Statement.lean with ` by\n  sorry` replaced by the proof.
- `/check` request shape (guide §"Iterating fast"): `{"target_id", "node_id", "content",
  "mode": "verify"}`; answer has `result.okay`, `lint[].code` (`imports-differ`,
  `helper-declarations`, `sorry-present`), `log_id`, `environment` (`lean-4.33.0`, AXLE hosts
  no 4.33.1; `exact: false`). Client: scratch `check.py` / `check2.py` (in the scratchpad).
- **Service lag:** `POST /check` with `target_id: erdos-1050` → `404 target-unknown`
  (`log_id 01M2QV4M5GDVSK91G7R0E6366D`). The service's products are rendered from graph commit
  `42f94ef` (`/frontier.json` and `/hosted-checkers.json` list 24 targets, no erdos-1050), and the
  graph's own `frontier.json`/`targets/index.json` on `origin/main` say the same `rendered_from`.
  The intake merged as `c1480c9` (#72) and the latest graph commit is `bdcd64e` (erdos-69's pin
  fix, saying #73's post-merge run rendered with the replaced gate) — so the post-merge render for
  the calibration intakes has not landed. Until it does, precheck/submit on erdos-1050 will be
  refused as `target-unknown`; `/check` can still be driven under another Erdős target's id
  (same Mathlib pin, same environment), which is what I do to iterate.

## Log of steps (append; newest last)

1. Read the handoff brief, calibration README, draft Statement/Witness/record, registry file,
   listed the live node. Created this file.
2. Read META/Context/gate-spec/target.yaml, the guide's precheck/check/token/submit sections,
   the step-2 rule. Baseline `/check` on erdos-1050 → 404 target-unknown (service lag, above).
3. Gallery prior art, top file (`LeanGallery/NumberTheory/Erdos1050/Statement.lean`, 139 lines,
   read through WebFetch): defines `Sliteral` as the literal tsum, proves `Sliteral = -1 + S`
   (S = the positive-denominator tail), and derives `erdos_1050` from `erdos_1050_S : Irrational S`
   (imported from `Lemma3.lean`) via `irrational_add_ratCast_iff`. So the gallery's structure is:
   reindex away the n = 0, 1 terms (−1 + 1), then Borwein's argument on the tail.

4. **Finding — the fast check is down for every Mathlib target.** `POST /check` under
   `target_id: erdos-376` (same Mathlib pin as erdos-1050), plain mode, on the erdos-1050
   statement: `log_id 01M2QV6GQ0YZBS53HXZ2DNZ20M`, `environment: lean-4.33.0`, `okay: None`,
   lint `['helper-declarations', 'sorry-present']` (the helper lint is expected here because
   the node id was erdos-376's), and `result.user_error` verbatim:
   `Unknown environment: lean-4.33.0. Available environments: lean-4.21.0, lean-4.22.0,
   lean-4.23.0, lean-4.24.0, lean-4.25.1, lean-4.26.0, lean-4.27.0, lean-4.28.0, lean-4.29.0,
   lean-4.30.0, lean-4.31.0, lean-4.32.2, lean-4.33.1, lean-4.34.0`
   (`execution_time_ms: 2`, request `606079ba-e9f0-4e16-96d5-47203a73994a`). AXLE has retired
   `lean-4.33.0` since the 2026-09-14 probe and now hosts `lean-4.33.1` — the exact pin — but
   `/hosted-checkers.json` still maps `0df444a3` → `lean-4.33.0`, `exact: false`, and the
   `core` entry too. So no `/check` call can elaborate anything right now (F13 mapping is stale;
   fix is one mapping edit on the network side, and it would make the check exact). Not mine to
   change; recorded for the lead.
5. Lead's message received (≈14:10 UTC): products stale (rendered_from `42f94ef`), the two
   post-merge runs since then failed (tag scan on erdos-412--h1, fixed in network 0401858 which
   every target now pins); a separate session is updating/merging intake PR #74 (erdos-402);
   its post-merge run should re-render products for all three targets, expected 14:30–14:50 UTC.
   Until then iterate on `/check` only; poll readiness with
   `git -C ../open_proof_network_graph fetch -q origin && git show origin/main:frontier.json | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['rendered_from'], [e for e in d['entries'] if 'erdos-1050' in json.dumps(e)][:1])"`
   and only then precheck and submit. Do not touch the graph or PR #74.
6. Gallery prior art, `Lemma3.lean` (~850 lines; read through WebFetch as a summary of
   statements, not proofs) and the directory listing: 18 files, ~350 KB of Lean
   (`Approximants.lean` 33.8 KB, `GeneralError.lean` 76 KB, `Residue.lean` 34.8 KB,
   `Lemma3.lean` 40 KB, `GeneralAssembly.lean` 21.5 KB, `QLagrange.lean`, `QBinom.lean`,
   `Pade.lean`, `Criterion.lean`, `Integrality.lean`, `Lambert.lean`, …). Structure: an
   irrationality criterion `irrational_of_intApprox` (integer sequences a, b with
   `b n * z - a n ≠ 0` and → 0), Borwein's Padé approximants with q-binomial / q-Lagrange
   identities, a 2-adic-plus-odd-denominator integrality argument for the numerators
   (`int_of_clearings`), the cleared error tending to zero, `irrational_zB`, then the series
   transferred to `S` by a rational shift. That is the whole of Borwein 1991/1992 formalized —
   hundreds of lemmas. **Judgment:** a full proof is out of reach in this timebox by a wide
   margin; the honest artifact is a checked skeleton whose holes are the lemmas of Borwein's
   argument, with the assembly (irrationality criterion + reindexing) proved.

7. **Workaround for the dead fast check:** AXLE is keyless at Stage 0 (F13-Q5,
   `api/opn_api/config.py` `DEFAULT_AXLE_URL = "https://axle.axiommath.ai"`), so I call it
   directly: `POST https://axle.axiommath.ai/api/v1/check` with
   `{"content", "environment": "lean-4.33.1", "timeout_seconds": 300}` (scratch `axle.py`).
   `GET /v1/environments` lists `lean-4.33.1` = `leanprover/lean4:v4.33.1` "with Mathlib"
   (the exact toolchain; its Mathlib is whatever AXLE built for it, not necessarily commit
   `0df444a3`, so a name could still differ from the gate's — precheck decides). Baseline: the
   sorry-bodied statement → request `0b243356-21d8-475e-93b7-456a2307cb6c`, `okay: true`,
   only `-:21:8-21:22: warning: declaration uses sorry`, 75 ms. The loop is live.
   Note the AXLE answer carries `failed_declarations` and `tool_messages.infos` with the goal at
   each sorry — useful for reading hole types.
8. Draft 1 (`scratch body1.lean` → `Proof1.lean`, assembled by `mk.py` so the statement prefix
   is byte-identical): one hole `borwein` (first `have`, closed statement, no locals: integer
   approximants a b : ℕ → ℤ for T = ∑' n, 1/(2^(n+3) − 3) with b n * T − a n ≠ 0 and → 0), then
   `criterion` (the Diophantine irrationality criterion, proved), `hpos`, `htail`/`hsum`
   (summability by comparison with (1/2)^n on the tail, `summable_nat_add_iff 2`), `hre`
   (S = T by `sum_add_tsum_nat_add 2`, the two leading terms −1 + 1 = 0). Result below.

9. Draft 1 on AXLE (request `c2aa50e1-3c72-4635-a959-37e8a0d6ad3d`, 490 ms, `okay: false`),
   two errors verbatim:
   `-:72:23-72:44: error(lean.unknownIdentifier): Unknown identifier `div_le_div_iff_of_pos``
   `-:81:10-81:30: error(lean.unknownIdentifier): Unknown identifier `sum_add_tsum_nat_add``
   Everything else (the criterion, hpos, summability shape, the hole) elaborated. Fixes: bound
   the tail with `one_div_le_one_div_of_le`; try `Summable.sum_add_tsum_nat_add` /
   `hsum.sum_add_tsum_nat_add 2` / `tsum_eq_zero_add` twice.
10. 14:14:45Z — products rendered: graph `origin/main` = `456997d gate: #74 pass` over
    `1f9fb28` (merge of #74), `frontier.json` `rendered_from 1f9fb28…` lists erdos-1050
    (`claimable: true`, `ready_since 2026-09-17T14:11:50Z`, `attempts: 0`, tags library
    Algebra/Data/NumberTheory/Topology). Precheck/submit on the target should now be possible
    once the live service picks the products up.

11. Lead's second message (≈14:16 UTC): go — PR #74 merged, main `456997d`, products live,
    erdos-1050 listed and claimable; precheck and submit; stop at a green gate check.
12. Partial-mode facts (guide §"Skeletonization", `gate/opn_gate/paths.py::locate`,
    `api/opn_api/submissions.py::check_artifact_path`, `gate/opn_gate/postmerge.py`):
    a partial's bundle path is `targets/erdos-1050/nodes/erdos-1050/attempts/<ts>-<pseudonym>-partial.lean`
    (any flat `.lean` under `attempts/` not ending `-alternate.lean` has role `partial`; no
    `<ts>` grammar is enforced by the api), `artifact_type: partial` on both precheck and
    submission, never `Proof.lean` (`artifact-path-mismatch`). The annex citation
    `-- annex: <sha256>` is optional (`annex_citation` → `None` when absent; children then get
    origin `compiler-derived` instead of `skeleton-hole`); it is validated only by the post-merge
    job (`check_annex_citation`, called at `postmerge.py:478`), so the partial's PR gate does not
    need the annex merged — **but the annex PR must merge before the partial PR**, or the
    partial's post-merge run fails `annex-uncited`. `POST /annexes` opens its own pull request
    (`appends.py`: one appended file, one branch, one pull request).
13. Token minting started 14:17:04Z: anonymous tutorial precheck job
    `01M2QVKHPRPXS6SVJ684EHJ8KS` (`state queued`, `authenticated False`), pseudonym
    `calib-1050-fable`, DCO version read from `/dco.json`. Scratch `mint.py` (token saved to
    scratch `token.json`, never printed). Then scratch `flow1.py` (background): `POST /annexes`
    with `annex.md` (the informal argument + prior art consulted, CC-BY-4.0) → cite its hash as
    the first body line → AXLE check → owned `POST /precheck` (`artifact_type: partial`, path
    `attempts/<ts>-calib-1050-fable-partial.lean`) → poll.

14. 14:22:46Z — owned precheck **pass** on every step (table in the State block). 14:23:0xZ —
    `POST /submissions` → 201, submission `01M2QVZJF8NSB70424HVM5VYZX`, **graph PR #78**;
    `tooling` disclosed as Claude Fable 5.1 (Claude Code agent, unattended, F15-T14c), harness
    "AGENTS.md walkthrough over HTTP; fast checks sent directly to AXLE lean-4.33.1". Now
    polling #78's checks (scratch `flow2.py poll`, and `gh pr view 78`).
15. 14:23:50Z — #78 (`partial: erdos-1050`, branch `submit/01M2QVZJF8NSB70424HVM5VYZX`, author
    `app/open-proof-network`, one file) — gate run `35233188330` IN_PROGRESS (job
    `105242323514`), postmerge job SKIPPED (runs only on merge), `mergeStateStatus BLOCKED`
    while the check is pending.

16. 14:26:36Z — #78 final: gate SUCCESS, postmerge SKIPPED (merge-time job), step 9 FAILURE
    (review required; verbatim message in the State block). The gate job's log shows the real
    run: `classify` → `"mode": "partial"`, "Precheck job `01M2QVS0GG8CR7JZ5T80N8V8C4` passed
    against graph commit `1f9fb286…`", attestation `"verdict": "pass"`, `"artifact_type":
    "partial"`, `model: "Claude Fable 5.1 (Claude Code agent, unattended calibration run
    F15-T14c)"`, `holes: ["borwein"]`. Stopped here, as instructed.


### Continuation (Mike: keep working, ~45 min from ≈14:30Z)

17. Lead's continuation brief: (1) the lead is merging #76 then #78 (sequenced); touch no PR until
    told the sequence is complete; the merge of #78 creates the hole child `erdos-1050--h1`
    (Borwein's theorem in approximant form) and the next submission goes on that child.
    (2) Meanwhile do the mathematics of the hole: formalize as much of Borwein's argument as
    closes (q-Padé approximants, remainder identity, integrality, remainder nonzero and → 0), a
    full proof of the hole if it closes, else an honest partial (holes before locals, F11-Q22;
    hazard-free ranges where possible). Check with the network's `/check` first (mapping being
    repointed to lean-4.33.1), fall back to direct AXLE. (3) When told the merges are done: read
    the child's `Statement.lean` and `META.yaml` on `origin/main` (note `hazards` without
    `acknowledged_hazards`, F07-Q19), precheck and submit on the child; if admission refuses on an
    unacknowledged hazard, type the refusal verbatim and stop. Commit nothing.
18. Mathematics of the hole (own analysis, before reading any construction). With
    `F(x) = ∑_{m≥1} 1/(2^m − x) = ∑_{k≥0} x^k/(2^(k+1) − 1)` (|x| < 2), `T = F(3)`, and the
    functional equation `F(x/2) = 2F(x) − 2/(2 − x)` gives `T = F(3/4)/4` (termwise:
    `1/(2^(n+3) − 3) = (1/4)·1/(2^(n+1) − 3/4)`), so the value can be moved inside the disc.
    A generic Padé/residue identity holds for any integer polynomial `Q` of degree `n`:
    `Q*(x)·F(x) − P_Q(x) = x^n ∑_m Q(2^{-m})/(2^m − x)` with `P_Q` having denominators dividing
    `M_n = ∏_{i≤n}(2^i − 1) ≈ 2^{n²/2}`. But `F` is meromorphic (poles at 2^m), so any Padé
    approximant at 0 has only a *geometric* error, while clearing `M_n` costs `2^{n²/2}`: the
    linear forms cannot tend to 0 — for any shift `3/2^j`, the size is ≈ `2^{n²/2 − jn}·9^n → ∞`.
    (Checked against the little q-Legendre polynomials, the orthogonal polynomials of the
    measure `∑ 2^{-m} δ_{2^{-m}}`: their norm `h_n ≈ 2^{-n}` and leading coefficient
    `≈ 2^{n(n−1)/2}` cancel the n² terms in the error, leaving a geometric rate.) This is *why*
    the problem was open until Borwein: the construction must (a) clear only
    `lcm_{l≤n}(2^l − 1)`-sized denominators, not the product (the gallery's `QPint n`, a product
    over `[n/2, n]` divisible by every `2^l − 1` with `l ≤ n − 1`, `≈ 2^{3n²/8}`), and (b) gain a
    `2^{−cn²}` error from a *multipoint* rational interpolation at the geometric nodes (the
    gallery's `muW`, "Vandermonde μ_j", q-Lagrange identity), plus a 2-adic/odd-denominator
    split for integrality (`int_of_clearings`). I cannot re-derive that construction with
    certainty in the box, and a hole with a false statement poisons a child node — so the
    child's decomposition must follow a construction that is known to be right. Reading the
    gallery's definition files next (statements only; recorded as consulted).

## Current best Lean source

Draft 2B — **checks on AXLE `lean-4.33.1`** (request `985477e4-1b4f-42b0-94d8-d684835c3de7`,
479 ms, `okay: true`, only `-:21:8-21:22: warning: declaration uses sorry`; the sorry is the one
hole `borwein`). Variant A (`Summable.sum_add_tsum_nat_add 2 hsum`) passed too
(`3ded8686-43aa-4e4c-9481-8a8592f4cd5a`); variant C failed: `Unknown identifier tsum_eq_zero_add`
(`07ec4845-6634-4c34-a4af-76c21f7ccc28`). Network `/check` verify mode on it: lint only
`['sorry-present']` (`log_id 01M2QVJ4S8JRCF24E9M82TZV98`) — no `helper-declarations`, no
`imports-differ`. Scratch copies: `best-body.lean`, `best-Proof.lean`. The full file:

```lean
/-
Copyright 2026 The Formal Conjectures Authors.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    https://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
-/

import Mathlib

/-! Erdős problem 1050 (calibration): a known result — imported from google-deepmind/formal-conjectures (FormalConjectures/ErdosProblems/1050.lean at c7f31d5fd3d2ca3d69979f2d213eb9b58fe956ae, Apache-2.0); as stated. A calibration target (Stages v3.17, F15-R14): a known result, drafted by docs/calibration_pool.py and read by the curator before intake. -/

theorem Opn.erdos_1050 :
    Irrational (∑' n : ℕ, (1 : ℝ) / ((2 : ℝ) ^ (n + 1) - 3)) := by
  -- Borwein's theorem for the tail T = ∑_{n ≥ 3} 1/(2^n − 3), in Diophantine-approximant form:
  -- integer sequences a, b with b n * T − a n never zero and tending to zero (Borwein 1991, 1992).
  have borwein : ∃ a b : ℕ → ℤ,
      (∀ n : ℕ, (b n : ℝ) * (∑' n : ℕ, (1 : ℝ) / ((2 : ℝ) ^ (n + 3) - 3)) - a n ≠ 0) ∧
      Filter.Tendsto
        (fun n : ℕ => (b n : ℝ) * (∑' n : ℕ, (1 : ℝ) / ((2 : ℝ) ^ (n + 3) - 3)) - a n)
        Filter.atTop (nhds 0) := by
    sorry
  -- The irrationality criterion: a real with such approximants is irrational.
  have criterion : ∀ x : ℝ, (∃ a b : ℕ → ℤ, (∀ n : ℕ, (b n : ℝ) * x - a n ≠ 0) ∧
      Filter.Tendsto (fun n : ℕ => (b n : ℝ) * x - a n) Filter.atTop (nhds 0)) →
      Irrational x := by
    rintro x ⟨a, b, hne, hlim⟩ ⟨r, hr⟩
    subst hr
    have hden : (0 : ℝ) < r.den := by exact_mod_cast r.den_pos
    obtain ⟨N, hN⟩ := (Metric.tendsto_atTop.mp hlim) (1 / r.den) (by positivity)
    have h := hN N le_rfl
    rw [Real.dist_eq, sub_zero] at h
    have hnum : (r : ℝ) * r.den = r.num := by exact_mod_cast Rat.mul_den_eq_num r
    have key : ((b N : ℝ) * r - a N) * r.den = ((b N * r.num - a N * r.den : ℤ) : ℝ) := by
      push_cast
      linear_combination (b N : ℝ) * hnum
    have hz : (b N * r.num - a N * r.den : ℤ) ≠ 0 := by
      intro h0
      have h1 := key
      rw [h0] at h1
      push_cast at h1
      rcases mul_eq_zero.mp h1 with h2 | h2
      · exact hne N h2
      · exact absurd h2 hden.ne'
    have hge : (1 : ℝ) ≤ |((b N * r.num - a N * r.den : ℤ) : ℝ)| := by
      exact_mod_cast Int.one_le_abs hz
    rw [← key, abs_mul, abs_of_pos hden] at hge
    have hlt : |(b N : ℝ) * r - a N| * r.den < 1 / r.den * r.den :=
      mul_lt_mul_of_pos_right h hden
    rw [one_div_mul_cancel hden.ne'] at hlt
    linarith
  have hT : Irrational (∑' n : ℕ, (1 : ℝ) / ((2 : ℝ) ^ (n + 3) - 3)) := criterion _ borwein
  -- The literal series is the tail: its first two terms are −1 and 1.
  have hpos : ∀ n : ℕ, (0 : ℝ) < (2 : ℝ) ^ (n + 3) - 3 := by
    intro n
    have h1 : (1 : ℝ) ≤ (2 : ℝ) ^ n := one_le_pow₀ (by norm_num)
    have : (2 : ℝ) ^ (n + 3) = 8 * 2 ^ n := by ring
    rw [this]
    linarith
  have htail : Summable (fun n : ℕ => (1 : ℝ) / ((2 : ℝ) ^ (n + 2 + 1) - 3)) := by
    refine Summable.of_nonneg_of_le (fun n => ?_) (fun n => ?_)
      (summable_geometric_of_lt_one (by norm_num : (0 : ℝ) ≤ 1 / 2) (by norm_num))
    · exact div_nonneg zero_le_one (hpos n).le
    · rw [one_div_pow]
      refine one_div_le_one_div_of_le (by positivity) ?_
      have h1 : (1 : ℝ) ≤ (2 : ℝ) ^ n := one_le_pow₀ (by norm_num)
      have : (2 : ℝ) ^ (n + 2 + 1) = 8 * 2 ^ n := by ring
      rw [this]
      linarith
  have hsum : Summable (fun n : ℕ => (1 : ℝ) / ((2 : ℝ) ^ (n + 1) - 3)) :=
    (summable_nat_add_iff 2).mp htail
  have hre : (∑' n : ℕ, (1 : ℝ) / ((2 : ℝ) ^ (n + 1) - 3)) =
      ∑' n : ℕ, (1 : ℝ) / ((2 : ℝ) ^ (n + 3) - 3) := by
    rw [← hsum.sum_add_tsum_nat_add 2]
    simp only [Finset.sum_range_succ, Finset.sum_range_zero]
    norm_num
  rw [hre]
  exact hT
```

## Errors seen (verbatim)

Every failure, typed as it came (R14 e); each is also in the timeline step named.

- Step 2 — `POST /check` (network) with `target_id: erdos-1050`:
  `{"error":"target-unknown","message":"erdos-1050 is not a target of this graph","details":{"log_id":"01M2QV4M5GDVSK91G7R0E6366D"}}`
  (HTTP 404; products stale, resolved by the lead's re-render at 14:11Z).
- Step 4 — `POST /check` (network) under `erdos-376`, AXLE's `result.user_error`:
  `Unknown environment: lean-4.33.0. Available environments: lean-4.21.0, lean-4.22.0, lean-4.23.0, lean-4.24.0, lean-4.25.1, lean-4.26.0, lean-4.27.0, lean-4.28.0, lean-4.29.0, lean-4.30.0, lean-4.31.0, lean-4.32.2, lean-4.33.1, lean-4.34.0`
  (still true at the end of the run; every network fast check answers `okay: None`).
- Step 9 — draft 1 on AXLE `lean-4.33.1`:
  `-:72:23-72:44: error(lean.unknownIdentifier): Unknown identifier `div_le_div_iff_of_pos``
  `-:81:10-81:30: error(lean.unknownIdentifier): Unknown identifier `sum_add_tsum_nat_add``
- Step 9 — variant 2C on AXLE: `-:82:8-82:24: error(lean.unknownIdentifier): Unknown identifier `tsum_eq_zero_add``
  (the names that exist at this Mathlib: `one_div_le_one_div_of_le`, `Summable.sum_add_tsum_nat_add`).
- Step 16 — #78's step-9 job (not a defect; the human-review gate):
  `##[error]step 9: this node's root has no fidelity certificate or registry provenance, so a non-author approving review is required before merge (D-4 v3.11; a curator record needs another listed curator's, F08-R8). Approving re-runs this check; the build above is not repeated.`

## Consulted (prior art / references, for the record — R14 c)

- Registry file `FormalConjectures/ErdosProblems/1050.lean` (google-deepmind/formal-conjectures at
  `c7f31d5f`): docstrings and the four statements (main, `two_pow_sub_one`, `borwein` general
  theorem, `transcendental` open variant). The main statement is the node's, verbatim.
- P. B. Borwein, *On the irrationality of ∑ 1/(q^n + r)*, J. Number Theory 37 (1991) 253–259;
  *On the irrationality of certain series*, Math. Proc. Camb. Phil. Soc. 112 (1992) 141–146 —
  cited from the registry and the target record; not fetched (the argument is Padé approximants
  to the q-series, and the summary of its Lean formalization below was enough to judge the size).
- External Lean 4 formalization `gotrevor/lean-gallery`, `LeanGallery/NumberTheory/Erdos1050/`
  (Trevor Morris with Claude Code and Harmonic's Aristotle): read through WebFetch as
  *summaries of statements* — `Statement.lean` (139 lines; `Sliteral = -1 + S`,
  `irrational_add_ratCast_iff`, `erdos_1050_S`) and `Lemma3.lean` (~850 lines; the 52 named
  declarations listed in step 6, ending in `borwein_integrality`, `irrational_zB` via
  `irrational_of_intApprox`, `erdos_1050_S`), plus the directory listing (18 files, ~350 KB).
  No proof text was copied; the skeleton's shape (rational shift to the positive tail, an
  integer-approximant irrationality criterion, Borwein's approximants as the hole) is the
  classical one and matches theirs. Everything in `best-Proof.lean` was written here and
  checked on AXLE.
- The contributor guide `../open_proof_network_graph/AGENTS.md` (`origin/main`), the gate's
  `paths.py`, `layout.py`, `postmerge.py`, the api's `checks.py`, `submissions.py`,
  `appends.py`, `axle.py`, `config.py`.

## Next

**Done by this agent:** annex PR #76 (green, CLEAN) and partial PR #78 (gate green; step 9 red
until a non-author approving review). Nothing further for the agent unless a fix is requested.

**For the lead (merge order):** (1) merge the annex PR #76 first (gate green, CLEAN) and wait
for its `gate: #76 pass` bot commit; (2) update #78's branch (strict up-to-date ruleset), let the
gate re-run, approve it as a non-author (step 9 — `gh run rerun --job <step-9 job id>` after
approving re-executes only that job, seconds, per the 2026-09-14 log entry), then merge. The
partial cites the annex, and the post-merge job refuses `annex-uncited` if the annex is not on
the node yet — so #76 must be on `main` before #78 merges. After the partial
merges, the post-merge job creates one child `erdos-1050--h1` (origin `skeleton-hole`) whose
statement is the Borwein hole: `∃ a b : ℕ → ℤ, (∀ n, (b n : ℝ) * (∑' n, 1/(2^(n+3) − 3)) − a n ≠ 0)
∧ Tendsto (…) atTop (𝓝 0)`; its witness is `True`-shaped (no hypotheses) and it will carry a
`div-zero` hazard at `1 / (2 ^ (n + 3) - 3)` that the bot cannot acknowledge (F07-Q19) — the
curator should acknowledge it as on the root (`2^(n+3) − 3 ≥ 5`, never 0).

**Toward a full proof (the child hole):** Borwein's argument is the whole of the gallery's
`Approximants/Residue/Integrality/Lemma3/Criterion` files; a session with a Mathlib checkout
(or the AXLE loop) and several hours could formalize it, in `have` steps or as a further
skeleton of the hole: (1) the q-Padé approximants as explicit finite sums with q-binomial
coefficients, (2) the identity `b n * T − a n = remainder n` by the q-Lagrange interpolation
argument, (3) integrality of `a n`, `b n` (2-adic part and odd part separately), (4) the
remainder is nonzero and tends to zero. The one-hole skeleton here is the honest artifact for a
50-minute box; do not submit a `Proof.lean` until every hole is proved (`dep-unproved`).

**Network defects found (for the lead, not mine to fix):** (a) `POST /check` is dead for every
target — AXLE retired `lean-4.33.0`, the mapping still names it (step 4); one mapping edit to
`lean-4.33.1` would also make the check `exact: true`. (b) The products lagged the calibration
intakes for ~2.5 h (post-merge runs failed) so the target was unknown to the service — lead's.
