# B: logical structure of MRSTT Theorem 1.3 (arXiv:2106.03335, read 23:20Z via ar5iv; paraphrased, check against the PDF before stating holes)

Setting: t large (depending on ε), solutions (n,m) of C(n,m) = t with 1 ≤ m ≤ n/2 ("left half", (1.4)).
Region R = {(n,m): exp(log^{2/3+ε} n) ≤ m ≤ n/2}.

Inputs:
- (1.5) m ≤ (1/log 4) log t + O(log log t)            [elementary: C(2m,m) ≥ 4^m/(2m+1)-type]
- (1.7) n/m ≍ exp(log t / m)                            [elementary-ish, Stirling]
- Prop 1.9 (distance estimate): two left-half solutions satisfy m' − m ≪_ε exp(log^{2/3+ε}(n+n'));
  if also m, m' ≥ exp(log^{2/3+ε}(n+n')), then n' − n ≪_ε exp(log^{2/3+ε}(n+n')).   [DEEP: Prop 1.12 equidistribution, Prop 3.2]
- Prop 1.10 (Kane-type): for a left-half solution (n,m) there is at most one other (n',m') with m' < m, n' > n and
  |m−m'| + |n−n'| ≪ exp((log log t)^{1−ε}).  [the proof actually uses the hypothesis with exp(O(log₂^{1−ε'} t)) — an O
  inside the exponent; Prop 2.1 (2.6)–(2.8) convexity of f_t, Lemma 2.2 (k=2), Corollary 2.3]

Deduction:
1. Take (n,m) ∈ R with the largest m. Every other solution in R has m' < m and n' > n (maximality + monotonicity of C(·,m)). [elementary]
2. From (1.5), (1.7) and m ≥ exp(log^{2/3+ε} n): m ≫ log t / (log log t)^{1/(2/3+ε)}, n, n' ≪ exp(O((log log t)^{1/(2/3+ε)})).
3. Prop 1.9 with small ε' (< ε/(2/3+ε)): m − m', n' − n ≪ exp(O((log log t)^{1−ε'})).
4. Prop 1.10 then allows at most one other solution in R.
5. So R holds ≤ 2 solutions.

Skeleton on --h3 following this: holes = Prop 1.9 (deep), Prop 1.10 (deep-ish, Kane-type), (1.5)+(1.7) size
estimates (elementary but Stirling-heavy); assembly = steps 1–5 with explicit constants replacing ≪. Caution: every
≪ must become ∃ C, and Prop 1.10's O-in-the-exponent hypothesis has to be stated in the form step 4 uses, or the
assembly will not close.
