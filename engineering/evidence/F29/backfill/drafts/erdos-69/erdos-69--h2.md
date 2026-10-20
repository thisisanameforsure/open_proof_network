---
label: Irrationality of the prime sum (untyped casts)
supersedes: null
drafted_with: Claude Fable 5.1 (claude-fable-5-1)
licence: CC-BY-4.0
---
$$\Bigl(\sum_{n=0}^{\infty}\frac{\uparrow\omega(n)}{2^{n}} = \sum_{p\ \text{prime}}\frac{1}{2^{\uparrow p}-1}\Bigr) \;\Rightarrow\; \sum_{p\ \text{prime}}\frac{1}{2^{p}-1}\notin\mathbb{Q}$$

If the series of ω(n)/2^n equals the sum over primes of 1/(2^p − 1), then that prime sum, taken in ℝ, is irrational. In the hypothesis the cast arrows ↑ carry no target type, so as written it is not the identity over ℝ that the parent's hole states: under Lean's numeral default both of its sides read in ℕ, where division rounds down and 2^p − 1 is truncated subtraction; only the conclusion, being `Irrational`, is over ℝ (∑' is the tsum, 0 when not summable).
