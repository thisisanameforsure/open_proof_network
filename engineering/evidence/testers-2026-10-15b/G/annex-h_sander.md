How Granville–Ramaré get (5.1) from their Lemma 5.1 ("By partial summation one can deduce", preprint p. 18), on the interval this node needs.

**Source.** A. Granville and O. Ramaré, Mathematika 43 (1996) 73–107, preprint p. 18: Lemma 5.1 (fix ε > 0 and J ≥ 1; there is c > 0 such that for y ≤ x^{1/J} the number of primes p ≤ y with {x/p^j} < σ_j for j = 1..J is σ₁⋯σ_J π(y) + O((y^{1−c(log y/log x)²} + y^{J/2+1+ε}x^{−1/2})(log x)^{4J})), taken from Sander [Sa2]; then (5.1) by partial summation. This node is hole `h_sander` of the level-2 skeleton on erdos-1094--h3--h3. Read by t1015b-g, 2026-10-15.

**The one hole, `h_l51`.** Lemma 5.1 with J = 1, weighted by log p and taken over the primes p with k/2 < p < 11k/20 (the difference of two values of y, and partial summation in p, which is how log-weighted counts follow from the unweighted lemma): for every C and δ > 0 there is K such that for k > K, k² ≤ C·n·log₂k and n < k², and for every σ in [0, 1],

|Σ_{p : {n/p} < σ} log p − σ Σ_p log p| ≤ δk.

On this range the lemma's error terms are o(k) uniformly in σ: y^{3/2+ε}x^{−1/2}(log x)^5 ≪ k^{1/2+2ε} since n ≫ k²/log k, and y^{1−c(log y/log x)²}(log x)^5 ≪ k^{1−c/4+o(1)} since n < k². The lemma's constants do not depend on σ, so K does not either. Written with x = n rather than GR's n − k (Lemma 5.1 is uniform in x).

**The assembly (proved in Lean): GR's partial summation, discretised.** Write f_p = {n/p} and L = Σ_p log p. For M ≥ 4/ε, f_p is within 1/M below (1/M)·#{1 ≤ j ≤ M : j/M ≤ f_p}. Swapping the two sums, Σ_p f_p log p is, up to L/M, (1/M) Σ_j Σ_{p : f_p ≥ j/M} log p, and by h_l51 at σ = j/M each inner sum is L − (j/M)L up to δk. Summing j/M over j (Gauss) gives L/2 − L/(2M), so |Σ_p (f_p − 1/2) log p| ≤ L/M + δk. The Chebyshev upper bound L ≤ θ(k) ≤ k log 4 ≤ 2k is proved in the assembly from Mathlib's `Chebyshev.theta_le_log4_mul_x`; with δ = ε/4 the total is at most εk.
