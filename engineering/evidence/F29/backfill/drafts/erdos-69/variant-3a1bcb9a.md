---
label: Irrationality of the omega series in factorial base
supersedes: null
drafted_with: Claude Fable 5.1 (claude-fable-5-1)
licence: CC-BY-4.0
---
$$\sum_{n=0}^{\infty}\frac{\omega(n)}{n!} \notin\mathbb{Q}$$

The sum over n ≥ 0 of ω(n)/n!, with ω(n) the number of distinct prime factors of n (so the n = 0 and n = 1 terms vanish), is irrational in ℝ. Every series is Mathlib's `tsum` over ℝ, which is 0 when the family is not summable, and `Irrational x` means x is not the cast of a rational.
