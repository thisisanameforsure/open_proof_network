---
label: Lambert-series identity for the omega series
supersedes: null
drafted_with: Claude Fable 5.1 (claude-fable-5-1)
licence: CC-BY-4.0
---
$$\sum_{n=0}^{\infty}\frac{\omega(n)}{2^{n}} = \sum_{p\ \text{prime}}\frac{1}{2^{p}-1}$$

The series of ω(n)/2^n over all n ≥ 0, with ω(n) the number of distinct prime factors of n (so ω(0) = ω(1) = 0), equals the sum over primes p of 1/(2^p − 1), both sides in ℝ. Every series is Mathlib's `tsum` over ℝ, which is 0 when the family is not summable.
