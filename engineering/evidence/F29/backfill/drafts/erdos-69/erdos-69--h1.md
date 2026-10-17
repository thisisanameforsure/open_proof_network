---
label: Lambert identity for the omega series (untyped casts)
supersedes: null
drafted_with: Claude Fable 5.1 (claude-fable-5-1)
licence: CC-BY-4.0
---
$$\sum_{n=0}^{\infty}\frac{\uparrow\omega(n)}{2^{n}} = \sum_{p\ \text{prime}}\frac{1}{2^{\uparrow p}-1}$$

The series of ω(n)/2^n over all n ≥ 0, with ω(n) the number of distinct prime factors of n, equals the sum over primes p of 1/(2^p − 1). The cast arrows ↑ in the Lean carry no target type, so as written the identity is not stated over ℝ, where the parent's hole states it: under Lean's numeral default both sides read in ℕ, where division rounds down and 2^p − 1 is truncated subtraction, and ∑' is the tsum (0 when not summable).
