---
label: "Chebyshev sum of log p over (k/2, 11k/20) is at least k/100"
supersedes: null
drafted_with: Claude Fable 5.1 (claude-fable-5-1)
licence: CC-BY-4.0
---
$$\exists K_3\in\mathbb{N}\ \forall k\in\mathbb{N}:\quad K_3<k \implies \frac{k}{100} \le \sum_{\substack{p \text{ prime}\\ k/2<p<11k/20}} \log p$$

For all large $k$, the sum of $\log p$ over the primes $p$ with $k<2p$ and $20p<11k$ is at least $k/100$. The sum is over `Finset.range k` filtered by `Nat.Prime p ∧ k < 2 * p ∧ 20 * p < 11 * k` (so $p<k$, which the second condition already forces), the logarithm is the real `Real.log` of the cast of $p$, and $k/100$ is real division of the cast of $k$.
