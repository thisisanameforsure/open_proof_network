---
label: Splitting a rescaled tail after k terms
supersedes: null
drafted_with: Claude Fable 5.1 (claude-fable-5-1)
licence: CC-BY-4.0
---
$$\forall N,k\in\mathbb{N}:\quad \sum_{j=0}^{\infty}\frac{\omega(N+1+j)}{2^{j+1}} = \sum_{j=0}^{k-1}\frac{\omega(N+1+j)}{2^{j+1}} + \frac{1}{2^{k}}\sum_{j=0}^{\infty}\frac{\omega(N+k+1+j)}{2^{j+1}}$$

Under the hypothesis that the Lambert identity ∑_{n≥0} ω(n)/2^n = ∑_p 1/(2^p − 1) holds, the rescaled tail T(N) equals its first k terms plus T(N+k)/2^k, for all naturals N and k. Here T(M) denotes the rescaled tail ∑_{j≥0} ω(M+1+j)/2^{j+1}, a tsum over ℝ (0 if not summable), and ω(n) is the number of distinct prime factors of n.
