---
label: Some rescaled tail times b is not an integer (untyped casts)
supersedes: null
drafted_with: Claude Fable 5.1 (claude-fable-5-1)
licence: CC-BY-4.0
---
$$\Bigl(\sum_{n=0}^{\infty}\frac{\uparrow\omega(n)}{2^{n}} = \sum_{p\ \text{prime}}\frac{1}{2^{\uparrow p}-1}\Bigr) \Rightarrow \forall b\in\mathbb{N},\ b>0\ \ \exists N\in\mathbb{N}\ \ \forall z\in\mathbb{Z}:\ \uparrow b\cdot\sum_{j=0}^{\infty}\frac{\uparrow\omega(N+1+j)}{2^{j+1}} \ne \uparrow z$$

If the series of ω(n)/2^n equals the sum over primes of 1/(2^p − 1), then for every b ≥ 1 there is an N such that b times the tail ∑_{j≥0} ω(N+1+j)/2^{j+1} is no integer z. Every cast arrow ↑ in the Lean carries no target type, so as written neither the hypothesis nor the tail is stated over ℝ, where the parent's hole states them: their domain is whatever Lean's defaults assign (ℕ for a bare numeral, where division rounds down and 2^p − 1 is truncated subtraction), and ∑' is the tsum (0 when not summable).
