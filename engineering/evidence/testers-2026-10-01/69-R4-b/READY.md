# erdos-69: what is ready the day the definitions are admitted (69-R4-b, 2026-10-01)

Nothing here has been submitted or seen by the gate. Every file below passed `POST /check` (target erdos-69, mode
check, lean-4.33.1) with `Defs-v2.lean` pasted in place of `import Defs.Construction`; log ids are in 69-R4-b.md.
After admission the first act is to re-run every check with the real import (`python3 chk.py` then pastes nothing).

## 0. The file to admit: `Defs-v2.lean`, not `69-R2-b/Defs.lean`

Changelog v1 → v2:
1. **Header comment corrected.** v1 said the triples cover every depth ≤ 3M with M triples. That is true only for
   even M. For odd M the last triple is 3M-2, 3M-1, 3M+1 and depth 3M is not cancelled (`OddM.lean`: at M = 1,
   depth 3, the six points are distinct; kernel-checked). A frozen comment that states a false lemma would mislead
   every later prover. The tables themselves are RIGHT: no entry changed.
2. **Thirteen v1 definitions unchanged, byte for byte** (checked: the v1 body is a prefix of the v2 body). So
   Skeleton.lean, H1, H2, H3 needed no repair; all four re-checked against v2 and pass.
3. **Four definitions added** at the end: `omegaBelow z n` (distinct prime factors ≤ z), `tailBelow`,
   `signedTailBelow`, `charMeanBelow` (the same objects with ω cut at z). Why now: the decay hole cannot be split
   into separately failing statements without naming "the small-prime part"; a defs file can never be edited, so
   adding them later means a second file. `charMeanBelow … (primorial z)` is the independent-primes model exactly
   (the cut combination is periodic in t with period z#), so no separate "model" definition is needed.
4. Not changed, deliberately: nothing made computable (the digit tables, indices, sign, dil, shift already are; the
   M = 2 `decide +kernel` test still runs); M = 0 stays allowed (one line, no cancellation; every statement that
   needs cancellation carries `Even M`, and h4e/h4f carry `0 < M`).

Evidence that the tables are right, now at general M (this was the curator's condition): `H4a.lean` (cancellation at
every depth 1..3M, all even M, all P), `H4b.lean` (the 2^-3M factorisation, for ω and for ω cut at any z),
`H4c.lean` (for u > 3M the line 2…2 is alone on its point at depth u; sharp, since lines 1 and 2 of an even triple
r meet at u = 3r+4). All three are complete proofs, no sorry. Each reads every entry of both tables for both parities.

## 1. A blocker the definitions alone do not remove

The root's `Statement.lean` imports Mathlib only, a proof or partial must keep the statement's header, and the one
import a proof may add is the node's own Context. So **no partial on `erdos-69` can mention `Opn.E69.*`**, and the
holes the gate would write under the root carry the root's header. `69-R2-b/Skeleton.lean` (holes h1..h4 stated
over the definitions) cannot be the root's partial as it stands, admitted file or not. (Inference from the guide,
not tested against the gate; the gate builder should confirm.)

Way round it, built and checked: one hole stated over Mathlib alone.
- `BridgeRoot.lean`: the root proved from a single hole `bridge` (a finite signed family of dilated tails with
  coprime steps, small reciprocal budget and small characteristic mean; no rationality, no definitions) plus the
  proved node spec-84446025. Mathlib-only; could be sent today as far as its header goes.
- `Bridge.lean`: the bridge statement as a theorem whose header imports `Defs.Construction`, proved from
  h1, h2, h3, h4 (as `have` holes) and the proved node spec-e0b917d1.
The bridge has to live in a node whose own header imports the definitions, i.e. a proposed node
(`POST /proposals/speculative`, whose statement header may import `Defs.*`), not a gate-written hole of the root.
Open question for the owner/gate builder: can the root (or its bridge hole) be closed through a proposed node of
identical statement? If the new defs route also lets gate-written holes import the target's Defs, none of this is
needed and Skeleton.lean in `have` form goes straight onto the root.

## 2. Submission order

| # | file | node | route | depends on |
|---|---|---|---|---|
| 0 | Defs-v2.lean → `targets/erdos-69/defs/Construction.lean` | (defs) | curator PR through the new gate mode | the gate change + re-pin |
| 1 | annex: 69-R2-b/annex.md is merged (#341, hash eca55f2b…); add a short annex for the bridge if the gate wants the skeleton's own | erdos-69 | `POST /annexes` | none |
| 2 | Bridge statement (signature of `Opn.erdos_69_signed_family_bridge`, header `import Mathlib` + `import Defs.Construction`, body sorry) | new node `spec-…` | `POST /proposals/speculative`, deps spec-e0b917d1 | 0 |
| 3 | BridgeRoot.lean body (drop the restated node; `-- annex:` line first) | erdos-69 | partial (`artifact_type: partial`), precheck, `POST /submissions`; deps spec-84446025 | see open question; needs 2 only if the hole is closed through the node |
| 4 | Bridge.lean body (drop the restated node; `-- annex:` line) | the bridge node | partial | 2 merged |
| 5 | witnesses for the four holes of 4 | `<bridge>--h1..h4` | `POST /proposals/witness`; h1: `∃ M d, True` shape; h2, h3: M = 0, P = 1; h4: q = 1, ε = 1 (later holes inherit earlier ones as hypotheses, which H1–H3 prove) | 4 merged |
| 6 | H1.lean, H2.lean, H3.lean | `<bridge>--h1, --h2, --h3` | `mode: verify` with node_id, precheck, submit as proofs | 5 |
| 7 | H4Skeleton.lean body | `<bridge>--h4` | partial | 5 |
| 8 | witnesses, then H4a.lean, H4b.lean, H4c.lean | `<bridge>--h4--h1, --h2, --h3` | witness, verify, proof (H4b's text uses h4a: at submission it arrives as the inherited hypothesis; delete the pasted copy of H4a and use the hypothesis) | 7 |
| 9 | h4g (parameters) | `--h4--h7` | elementary, NOT yet proved | 7 |
| 10 | h4d, h4e, h4f | `--h4--h4, --h5, --h6` | open; see below | 7 and a number theorist |

Hole ids are assigned by the post-merge job; read them from the merge, do not assume the numbering above. Every
theorem name in H1–H4c is the R2 guess (`erdos_69__h4__h1` …); rename to what the hole's Statement.lean says, and
expect each gate-written hole to carry its predecessors as hypotheses (adapt by `intro`).

## 3. The seven holes of h4 (H4Skeleton.lean; assembly complete, checked)

| hole | says | status | class |
|---|---|---|---|
| h4a | signed count of lines through any point is 0 at depths 1..3M, M even | **proved** | elementary |
| h4b | signedTail = 2^-3M × signed tails started 3M later (ω and ω≤z) | **proved** (from h4a) | elementary |
| h4c | for u > 3M the line 2…2 shares its depth-u point with no other line | **proved** | elementary |
| h4d | ∃C: mean over t < z^A of |signedTail − signedTailBelow z| ≤ C (3/4)^M (1 + log A), z ≥ modulus | open | needs Mertens (spec-7d098d5c) + h4b; no other analytic input that I can see; believed true |
| h4e | ∃K'(q,η): for every even M>0, P, z ≥ modulus there is A ≤ K'·100^M·(1+log₂log₂log₂ z) with ‖charMeanBelow(z^A) − charMeanBelow(z#)‖ ≤ η | open | **analytic input Mathlib lacks** (a multi-shift fundamental lemma of dimension about 6^M·depth); **truth unknown**: the A bound is my guess at what a sieve gives |
| h4f | ∃K(q,η): ‖charMeanBelow(z#)‖ ≤ η once z ≥ modulus and z ≥ P^(2^(K·100^M)) | open | CRT product + divergence of Σ1/p (Mertens node) + a quantitative κ; **truth unknown in this quantitative form** (needs κ_M ≥ c/100^M; h4c gives one isolated line per depth at the same depth only; coincidences across depths are not yet excluded in Lean) |
| h4g | the parameters fit: ∃ M P z with all the size constraints, and C(3/4)^M(1+log A) ≤ η for every admissible A | open | elementary real arithmetic; believed true (checked by hand: log₂log₂log₂ z = O(M + log K + log 1/η)); a seventh hole, added so the assembly is 60 lines |

Circularity, each hole: h4a, h4b(ω-free part), h4c, h4g do not mention ω or irrationality. h4d–h4f are statements
about ω along fixed progressions with no rationality hypothesis; none implies the root without the others plus
spec-84446025, and the root (irrationality of one number) gives no control of a mean over t of phases, so none
follows from the root in a few lines. All hypotheses are satisfiable (M = 2, P = 49 and any admissible n₀, which h3
supplies); nothing is shaped `… → False`. I did not get a gate ruling on any of them.

## 4. For the owner: what is uncertain

This is not the Tao–Teräväinen proof. Their argument (arXiv:2512.01739, Theorem 1.3) cancels with a cube of prime
dilations, keeps total weight 1, and needs a two-point correlation estimate for the large prime factors. The route
here cancels with products of hexagons of rough dilations, is left with weight (3/4)^M, and claims the triangle
inequality plus Mertens is then enough for the large primes. What is now machine-checked is only the combinatorics
(the tables cancel exactly at every even M, something survives at every later depth) and the two assemblies (root
from bridge, h4 from seven holes). **None of the analysis is checked, and two of the analytic holes (h4e, h4f) are
stated with quantitative shapes I chose so that the parameters close; I do not know that they are true in that
shape.** The specific doubts: (1) h4e needs a fundamental lemma uniform in a number of shifts that grows like
6^M·(M + log log log z); I sized A from the standard heuristic, not from a proof. (2) h4f needs the local factors
to stay away from 1 at rate about 100^-M; R3's numerics suggest about 11^-M, but only for M ≤ 5, and the parameters
the argument needs (log P > 5·6^M/ε) are far beyond any computation. (3) The depth of the tails is infinite while
every sieve statement is about finitely many shifts; the truncation is inside h4e and I have not written it out.
(4) If the route is right it proves a 2025 theorem of Tao and Teräväinen without the ingredient they call essential.
That is possible, and it is exactly the claim a number theorist should read before the network shows progress on
this target: a wrong h4e would leave proved lemmas h1–h3, h4a–h4c on the record under a hole that can never close.
My recommendation: admit Defs-v2 (the proved lemmas now vouch for the tables), submit through step 8, and hold
h4d–h4f as open holes labelled unreviewed until someone qualified has read section 2 of 69-R3-b/H4-VERDICT.md and
the three statements above.
