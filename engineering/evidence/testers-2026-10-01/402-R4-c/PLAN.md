# 402-R4-c PLAN: the prime criterion for erdos-402, clean-room (2026-10-01)

Nothing was submitted. Not opened: `402-R3-b/upstream-plby-Erdos402.lean.txt`, the scratchpad `lean-proofs`
clone, the upstream repository. Everything below is my own derivation from the mathematics described in
`402-R3-b/FINDING.md` (residues mod a prime just below 2n, a "rectangle" for repeated quotients).
I did not fetch arXiv 2005.04429: the derivation closed without it.

## 0. Headline
1. **The criterion is simpler than the record says, and it is fully formalised.** The target's negation is
   *strict* (every quotient a/gcd(a,b) < n). With strict quotients **the second prime q is not needed**:

   > p prime, n < p < 2n, (2n − p)² ≤ n  ⟹  every set of n positive integers has a, b with n·gcd(a,b) ≤ a.

   (This is Zaharescu's Proposition 1 as FINDING.md quotes it. The q of the B–S chain is needed for
   non-strict quotients / the wider windows (2n − p)² ≤ (j+1)n, j ≥ 1, not here.)
2. **Lean, fast-checked at the pin (lean-4.33.1, exact env, okay true, no sorry):**
   `Criterion.lean` (5 declarations, 363 lines) and **`CriterionSingle.lean`: the same proof as ONE
   declaration, 379 lines, inside the 200k-heartbeat cap**, in the target's ℚ form. No helper declarations,
   no `native_decide`, no axioms beyond Mathlib's.
3. **`skeleton-window.lean`** (405 lines, okay true, lint `sorry-present` only): a skeleton for the open hole
   `erdos-402--h3-v2--h1--h1--h1` with the criterion inlined and ONE hole `hwin` whose conclusion is the positive
   disjunction "good pair ∨ a window prime exists". Not sent.
4. **Window primes are certified for 681 ≤ n ≤ 200014** by 18 fast-checked declarations (`Window/*.lean`,
   1773 primes, `norm_num` primality, 100 primes per declaration fits the cap; 200 does not).
5. **Residual below 200014: seven open n, not 43:** 63, 105, 111, 153, 165, 679, 680. (All exceptions of the
   criterion in 2..200000: 5, 8, 14, 18, 48, 61, 62, 63, 74, 105, 111, 153, 165, 270, 677, 678, 679, 680; the
   other eleven are n prime or prime + 1, already excluded by the hole's hypotheses.) cert.py's 43 came from
   requiring q.
6. **All n is NOT reachable by this criterion with any known theorem:** "a prime in [2n − √n, 2n) for all
   large n" is a prime-gap statement of Legendre strength (gaps below √(x/2)); it is open even under RH.
   So the analytic node cannot be "a window prime exists for large n"; it has to be "Graham for large n" by
   the B–S/Zaharescu route (wider windows + counting), which is a different and much longer proof.

## 1. The argument, with proofs (n = |A|, all quotients a/gcd(a,b) < n, p prime, n < p < 2n, k = 2n − p, k² ≤ n)
Notation: for a ≠ b in A write g = gcd(a,b), a = x·g, b = y·g, gcd(x,y) = 1, 1 ≤ x, y ≤ n − 1 < p.
Let R(a) = a / p^{v_p(a)} (the p-free part) and ρ(a) = R(a) mod p ≠ 0.

**L1 (pair lemma; Lean `r4c_pair`).** a·y = b·x. Taking p-free parts (multiplicative; x, y are their own
p-free parts because they are below p): R(a)·y = R(b)·x, so ρ(a)·y = ρ(b)·x in the field Z/p.
- ρ(a) = ρ(b) ⟹ y ≡ x (mod p) ⟹ x = y (both below p) ⟹ a = b.
- ρ(a) = −ρ(b) ⟹ p | x + y, and 0 < x + y < 2p ⟹ **x + y = p**.
No valuation bookkeeping is needed (the "equal p-adic valuation" step of the orientation is true but unused).

**Fold class.** c(a) = min(ρ(a), p − ρ(a)) ∈ [1, (p−1)/2] (p is odd since n < p < 2n). c(a) = c(b) iff
ρ(a) = ±ρ(b). So: c(a) = c(b), a ≠ b ⟹ x + y = p.

**L2 (rectangle lemma; Lean `r4c_arith`, `r4c_rect_core`, `r4c_rect`).** Let α + β = p, gcd(α,β) = 1,
α, β ≤ n − 1 (hence both > n − k), u, w ≥ 1. If the four cross quotients of the pairs (αu, βw) and (βu, αw) are
all below n, then u = w.
*Proof.* Write u = d₁C, w = d₂C with gcd(d₁,d₂) = 1; quotients do not see C. Put e_i = gcd(α,d_i),
f_i = gcd(β,d_i). Then gcd(αd₁, βd₂) divides gcd(αd₁,β)·gcd(αd₁,d₂) = f₁·e₂ and likewise
gcd(βd₁, αd₂) | e₁·f₂; also e₁f₁ | d₁, e₂f₂ | d₂, e₁e₂ | α, f₁f₂ | β (coprimality). The four hypotheses give
α e₁ < n e₂, α e₂ < n e₁, β f₁ < n f₂, β f₂ < n f₁.
Arithmetic step: if e₁ < e₂ then α(e₁+1) ≤ αe₂ < n e₁, so α < s·e₁ with s = n − α < k; and
e₁(e₁+1) ≤ e₁e₂ ≤ α < s e₁ gives e₁ + 1 < s, so α < s² − 2s; but α = n − s ≥ k² − s ≥ (s+1)² − s. Contradiction.
So e₁ = e₂, and being coprime, e₁ = e₂ = 1; same for f. Then gcd(αd₁,βd₂) = 1, αd₁ < n, and 2α > n
(α ≥ k from k² ≤ n < α + k) forces d₁ = 1; same for d₂. ∎
Numerics (`num.py`): 294,292 cases, 0 violations; **sharp**: with k² > n allowed there are violations at once
(n = 18, p = 29, α = 12, u = 3, w = 4).

**L3 (count; Lean `r4c_criterion`).** Split A into A₂ = {a : some a′ < a in A has c(a′) = c(a)} and A₁ = the rest.
- c is injective on A₁ (of two elements with equal class the larger is in A₂), so |A₁| ≤ (p−1)/2.
- For a ∈ A₂ pick such a partner a′; by L1, a = x g, a′ = y g, x + y = p. Map a ↦ max(x,y) ∈ [(p+1)/2, n−1].
  This map is injective on A₂: if a, b ∈ A₂ have the same max then {x_a,y_a} = {x_b,y_b} =: {α,β} and
  {a, a′, b, b′} = {αu, βu, αw, βw}; L2 gives u = w, so either a = b, or a = b′ < b = a′ < a, absurd.
  So |A₂| ≤ n − (p+1)/2.
- n = |A₁| + |A₂| ≤ (p−1)/2 + n − (p+1)/2 = n − 1. Contradiction. ∎
(The "no three elements in one class" fact and disjointness of the two pairs are not needed.)

Special case worth knowing: if 2n − 1 is prime the theorem is immediate (x + y = 2n − 1 with x, y ≤ n − 1 is
impossible; A₂ is empty).

## 2. Lean delivered (all in `402-R4-c/`, all fast-checked, env lean-4.33.1 exact)
| File | What | Result |
|---|---|---|
| `Arith.lean` | `r4c_arith` | okay |
| `Rect.lean` | + `r4c_rect_core` | okay |
| `Pair.lean` | `r4cCls` (def), `r4c_pair` | okay |
| `Criterion.lean` | all five declarations incl. `r4c_rect`, `r4c_criterion` (ℕ form: `A.card * a.gcd b ≤ a`) | okay |
| `CriterionSingle.lean` | **one declaration**, lemmas as `have`s, class function obtained with its equation instead of a `def`; ℚ form of the target | okay, under 200k heartbeats |
| `skeleton-window.lean` | skeleton on `erdos-402--h3-v2--h1--h1--h1`, one hole `hwin` | okay (`sorry-present`) |
| `Window/r4c_window_<lo>_<hi>.lean` ×18 | ∀ n ∈ [lo,hi] ∃ p prime, n < p < 2n, (2n−p)² ≤ n | all okay (`Window/RESULTS.txt`) |
| `assemble.py`, `cover.py`, `num.py`, `chk.sh` | generators and tests | |

## 3. Size and fit with the network's constraints
- Criterion: 379 lines as a single declaration, measured, passes the cap. FINDING.md's estimate ("thousands of
  lines, needs an auxiliary-lemma feature") does not apply to the strict j = 0 criterion. **No new protocol
  feature is needed for the criterion.**
- Finite range: one `norm_num` primality certificate per ~√n/2 consecutive n; 100 per declaration. To 2·10⁵:
  18 declarations. To 10⁶ about 40, to 10⁷ about 127 (cost per certificate grows like √p). These cannot be
  `have`s of one skeleton (18 × ~150k heartbeats); they must be separate nodes: either 18 holes of one skeleton
  (each a closed statement, trivially witnessed) or, better, a protocol feature **"proved lemma nodes a proof may
  import as deps"** (R2-b's F2). Without it, a partial with 18 holes is legal but clumsy.
- What would NOT fit: the j ≥ 1 analysis (r_p ≤ 2, shapes ℓ·Y(Y+1), prime q) for the seven residual n, and the
  B–S large-n argument. Those are the "thousands of lines"; my guess is 1,500–3,000 lines for j ≤ 3 clean-room,
  which does need lemma nodes (several declarations each near the cap).

## 4. Residual and proposed node layout
Let W(n) := ∃ p prime, n < p < 2n ∧ (2n−p)² ≤ n.
1. **criterion** (elementary, DONE here): W(|B|) ⟹ good pair. As the assembly of `skeleton-window.lean`.
2. **hole `hwin`** (what the skeleton leaves): hypotheses of the parent ⟹ good pair ∨ W(|B|). True for every B
   (the pair disjunct is Graham's theorem); hypotheses satisfiable (same hypothesis list as the parent, so the
   parent's witness, 402-R3-a/next-next-hole-witness.lean style, should carry over; not re-checked here).
   Next skeleton on `hwin`, three positive parts:
   - **finite-certified**: ∀ n, 681 ≤ n ≤ 200014 → W(n). Computational, `norm_num`, DONE as 18 checked files;
     plus the non-exceptional n < 681 (same generator, not run: non-contiguous blocks).
   - **seven small n**: |B| ∈ {63, 105, 111, 153, 165, 679, 680} ⟹ good pair. Needs the j ≥ 1 rectangle analysis
     with the prime q (B–S Lemmas 2.2–3.3) or per-n arguments. Honest, hard, elementary. (FINDING.md says the
     shape certificate covers all of these; only 27 and 65 fail it, and those two have window primes 53 and 127,
     i.e. are closed by item 1.)
   - **large n (parked)**: |B| > 200014 ⟹ good pair ∨ W(|B|). NOT provable as "W(n) for all large n" with known
     mathematics (see 0.6). Either extend the certified range by computation as far as wanted (each decade costs
     ~3× more declarations), or formalise B–S §4–5 (needs PNT with error term, not in Mathlib). The target cannot
     be closed for all n without that; say so on the record rather than leave a hole that looks elementary.
3. Suggested honest restatement for the owner: resolve "Graham for n ≤ N" (N = 200014 now) as its own variant
   root is forbidden by rule 4, so instead keep one root and let `hwin`'s large-n part be the single parked node,
   labelled analytic.

## 5. Caveats
- Fast check only; no precheck, no gate run. The skeleton's header is not byte-identical to the node's
  Statement.lean (Context import, doc comment); fix before any precheck. Hole round-trip (`hole-not-roundtrip`)
  untested: `hwin` contains ℚ casts copied from the node's own printed statement, and ℕ subtraction `2 * B.card - p`.
- "27 and 65 closed by item 1" and the seven residual n rest on `num.py` (sieve), not on Lean.
- The claim in 0.6 about prime gaps is from general knowledge, not checked against a source today.
