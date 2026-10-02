# h4e and h4f under stress (69-R5-a, 2026-10-01)

Neither statement is proved here. What follows is: the exact structure both rest on, a proof sketch of h4f that I
believe is complete and elementary, what h4e needs and where the risk is, the numerics, and one recommended change of
shape before anything is frozen. Everything in this file is my own argument, unchecked by a kernel or a referee.

## 0. The structure (exact, all from h4b)
For even M and an admissible base, with W = modulus, and after h4b,
  signedTailBelow z (t) = Σ_{p ≤ z} f_p(t),   f_p(t) = Σ_{(d,u), u > 3M, p | n₀ + x_{d,u} + W t} sign(d) 2^-u,
where x_{d,u} = shift_d + dil_d·u.
- p ≤ P: all dilations are 1 and all shifts are 0 mod p, so f_p(t) = Σ_u 2^-u [p | n₀+u+Wt] · Σ_d sign(d) = 0. Exactly.
- p | W: the condition does not depend on t. A constant phase.
- other p ≤ z: f_p depends on t mod p only, and the residues are independent over a full period (CRT). So
  charMeanBelow(z#) = phase × ∏_{P<p≤z, p∤W} φ_p,  φ_p = (1/p) Σ_{a mod p} e(q C_p(a)),
  C_p(a) = Σ_{(d,u): n₀+x_{d,u} ≡ a (p)} sign(d) 2^-u.   (`model.py` computes exactly this.)

## 1. h4f (the model decays): TRUE in the stated shape, as far as I can see; sketch
Claim: 1 − |φ_p| ≥ c·q²·64^-M / p for all primes P < p ≤ z outside a set B with Σ_{p∈B} 1/p ≤ c_q·6^M. Then
|∏ φ_p| ≤ exp(−c q² 64^-M (log log z − log log P − C₀ − c_q 6^M)) and the hypothesis z ≥ P^(2^(K·100^M)) gives
log log z − log log P ≥ K·100^M·log 2, so K ≥ C(q)·log(1/η) is enough. The stated 100^M has room: 64^M is needed.
1. Pick the depth u₀ = max(3M+1, ⌈log₂ q⌉+2) and the line d₀ = 2…2. By h4c no other line passes through the same
   integer point at depth u₀. Let U = u₀ + ⌈2.6M⌉ + 3, so that 6^M·2^-U ≤ 2^-(u₀+2).
2. A prime p > P is BAD if some (d,u) ≠ (d₀,u₀) with 3M < u ≤ U lands on the same residue as (d₀,u₀). That means
   p | N for a specific integer N = x_{d,u} − x_{d₀,u₀}. N ≠ 0: at the same depth by h4c; at different depths because
   N ≡ u − u₀ (mod P#) and 0 < |u − u₀| < P#. |N| ≤ 4^P·poly, so N has at most 2P/log P + O(1) prime factors above P;
   there are 6^M·(U−3M) pairs; each bad prime has 1/p < 1/P. Total bad reciprocal mass ≤ 6^M·(U−3M)·3/log P = O_q(6^M).
3. For a good p: C_p(a₀) = ±2^-u₀ + (tail of depths > U), |tail| ≤ 6^M 2^-U ≤ 2^-(u₀+2). So q·C_p(a₀) lies between
   (3/4) q 2^-u₀ and (5/4) q 2^-u₀ ≤ 5/16 in absolute value: the unit vector v_{a₀} = e(q C_p(a₀)) is at angle
   ≍ q 2^-u₀ from 1. The total mass Σ_a |C_p(a)| ≤ (3/4)^M, so all but 4·6^M·(…) classes a have |q C_p(a)| less
   than half of that angle; for p ≥ 16·6^M that is at least p/2 classes (the primes in (7^M, 16·6^M) have O(1) mass).
4. For unit vectors, p²(1 − |φ_p|²) = Σ_{a<b} |v_a − v_b|² ≥ Σ_{b near 1} |v_{a₀} − v_b|² ≥ (p/2)·c (q 2^-u₀)².
   Hence 1 − |φ_p| ≥ c q² 4^-u₀ / p ≥ c' q² 64^-M / p (for the finitely many M with 2^(3M) < 4q the constant depends
   on q, which K may).
5. Σ_{P<p≤z} 1/p = log log z − log log P + O(1) is the Mertens node; the primes dividing W have mass ≤ 6^M·5/log P by
   the proved node spec-e0b917d1.
Ingredients: h4c, the Mertens node, spec-e0b917d1, CRT. No sieve. Formalisation: the CRT product formula over a
primorial period is the laborious part (several hundred lines); nothing in it is analytic.
Numerics (`model.py`, exact residues, double-precision phases):
- M = 2, P = 49 (the smallest admissible P), primes up to 20000: κ_eff = −log|∏φ_p| / Σ1/p = 0.0614 for q = 1, equal
  to three digits to the integer-coincidence value 0.0614 that 69-R3-b computed; NO prime has p(1−|φ_p|) below half
  of it for q ≤ 8 (min 0.041). So collisions mod p do not degrade the decay even at the smallest P.
  κ_eff·64^M = 251, κ_eff·100^M = 614: the claimed rate is beaten by orders of magnitude (true rate is about 11^-M).
- q a multiple of 2^(3M) (q = 64, 128, 192 at M = 2): κ_eff is LARGER (120–180), not zero; a few primes fall below
  half the integer value but none near zero (min 43). No bad denominator.
- M = 4, P = 2401 (1296 lines, modulus of 1.3 million digits), primes in (2401, 3600]: κ_eff = 5.15e-4 for q = 1 against the integer value 5.18e-4; no prime below half of it for q ≤ 4096; κ_eff·64^M = 8.6e3.
I looked for a failing regime: (a) q with q·c_x ∈ ℤ for every point — impossible, depths are unbounded and each
depth > 3M has an isolated line (h4c); (b) P close to 7^M so that lines collide mod p — covered by step 2, and the
M = 2, P = 49 run shows none; (c) M small against q — step 1's choice of u₀. I found no counterexample.

## 2. h4e (small primes behave independently): PLAUSIBLE, NOT VERIFIED; this is the one real risk
What it says: the mean of F(t) = ∏_{p≤z} e(q f_p(t)) over t < z^A is within η of the product of the local means,
for some A ≤ K'·100^M·(1 + log₂log₂log₂ z), for every z ≥ W. This is a Kubilius-model statement for
R = 6^M·(U − 3M) linear forms n₀ + x_{d,u} + W t at once.
- The depths must be cut at some U first. The cost in L¹ is q·6^M·2^-U·(mean of ω_{≤z}) ≈ q·6^M·2^-U·log log z, so
  U ≈ 2.6M + log₂ log log z + log₂(q/η). THIS is where the triple logarithm in the statement comes from: the number
  of forms R grows like 6^M·(M + log log log z). (Primes dividing W need no cut: they are a constant phase.)
- With R forms and local densities ≤ R/p, a fundamental lemma of dimension κ = R gives relative error about
  e^(9κ − s) with s = log T / log z = A (Friedlander–Iwaniec, Opera de Cribro, Cor. 6.10 has this shape, uniform in
  κ). So A ≈ 9·6^M·(U − 3M) + log(1/η) should do, against the stated room K'·100^M·(1 + log₂log₂log₂ z): the shape
  is consistent, with a factor (100/6)^M/M to spare.
- What I could NOT verify: (i) the passage from a sieve statement (non-negative weights, sifted sets) to the mean
  of the complex-valued F, i.e. a total-variation Kubilius model for κ forms with κ growing; the classical model
  (Kubilius, Barban–Vinogradov, Tenenbaum III.6) is for one form and constants depend on κ in the versions I know;
  (ii) the primes just above P where R ≥ p and the sieve density condition fails (they must be handled by an exact
  CRT conditioning; plausible, since e^R ≤ z^(o(A))); (iii) uniformity in n₀ and in z down to z = W.
  None of these looks like an obstruction. None is written down anywhere I can cite.
- No computation reaches the hypothesis: z ≥ W ≥ 10^685 already at M = 2. PROXY only (`h4e_proxy.py`, M = 2, P = 49,
  ω cut at z = 100, 300, 1000, i.e. z < W, outside the hypothesis): |empirical mean over t < T − model| falls from
  about 1e-3 at T = z^1.2 to 1e-6…1e-4 at T = z^2…z^3 for q = 1, 2, 5. The mechanism behaves; this is not evidence
  about the constants.
- Simultaneity in the regime h4g selects (M = 2m large, log₂ P = 6^M·D, log₂log₂ z ≈ K·100^M + 6^M·D): h4f needs
  log log z − log log P ≳ 64^M — supplied. h4e then has R ≈ 6^M·(9.3M + O(1)) forms and needs A ≈ 10·R ≈ 100·M·6^M,
  inside its bound. h4d (now proved) then costs C(3/4)^M(1 + log A) with log A ≈ 1.8M + log M → 0. The three are
  compatible; no hidden clash between the existentials. The one-way dependence is: K, K', C first (from q, ε), then
  M, then P, then z, then A — which is the order of the quantifiers in H4Skeleton.

## 3. Recommended change before h4e is frozen as a node: relax the A bound
h4g tolerates any bound on A whose logarithm is O(M) in the selected regime. With
  A ≤ K'·100^M·(1 + log₂log₂ z)²      (one logarithm fewer, squared)
h4g is still true — `H4g-relaxed.lean`, PROVED — and the assembly still closes — `H4Skeleton-relaxed.lean`, checked.
The relaxed h4e is implied by the stated one, so nothing is lost, and it is within reach of a Brun-type truncation
(expand ∏(1 + h_p), keep products of at most k primes, k ≈ e²·2R·log log z; the remainder is a moment bound for
the number of small prime factors of ∏ of the forms): no fundamental lemma, no dimension-uniform constants. That is
the difference between an analytic input "Mathlib lacks and nobody here can check" and a long but elementary
formalisation. Statements are immutable once merged, so this choice has to be made before the skeleton goes in.
