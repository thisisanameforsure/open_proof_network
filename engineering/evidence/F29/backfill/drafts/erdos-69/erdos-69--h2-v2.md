---
label: Irrationality of the prime sum 1/(2^p - 1)
supersedes: null
drafted_with: Claude Fable 5.1 (claude-fable-5-1)
licence: CC-BY-4.0
---
$$\Bigl(\sum_{n=0}^{\infty}\frac{\omega(n)}{2^{n}} = \sum_{p\ \text{prime}}\frac{1}{2^{p}-1}\Bigr) \;\Rightarrow\; \sum_{p\ \text{prime}}\frac{1}{2^{p}-1}\notin\mathbb{Q}$$

If the series of ω(n)/2^n over n ≥ 0 equals the sum over primes p of 1/(2^p − 1), then that prime sum is irrational, everything in ℝ with ω(n) the number of distinct prime factors of n. Every series is Mathlib's `tsum` over ℝ, which is 0 when the family is not summable, and `Irrational x` means x is not the cast of a rational.
