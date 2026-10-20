---
label: Closed form for the dilated tail
supersedes: null
drafted_with: Claude Fable 5.1 (claude-fable-5-1)
licence: CC-BY-4.0
---
$$\forall a,m\in\mathbb{N},\ a\ne 0:\quad \sum_{k=0}^{\infty}\frac{\omega\bigl(a(m+k+1)\bigr)}{2^{k+1}} = \sum_{k=0}^{\infty}\frac{\omega(m+k+1)}{2^{k+1}} + \omega(a) - \sum_{p\mid a}\frac{2^{\,m \bmod p}}{2^{p}-1}$$

For a nonzero natural a and any natural m, the tail of ω along the multiples a(m+k+1) equals the undilated tail plus ω(a) minus, for each prime factor p of a, 2^{m mod p}/(2^p − 1), all in ℝ, with ω(n) the number of distinct prime factors of n and the last sum over `a.primeFactors`. Every series is Mathlib's `tsum` over ℝ, which is 0 when the family is not summable.
