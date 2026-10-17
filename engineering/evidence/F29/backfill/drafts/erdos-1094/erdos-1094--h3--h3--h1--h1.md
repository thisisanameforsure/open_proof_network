---
label: "Prime number theorem: θ(x) ~ x"
supersedes: null
drafted_with: Claude Fable 5.1 (claude-fable-5-1)
licence: CC-BY-4.0
---
$$\forall \varepsilon>0\ \exists X\in\mathbb{R}\ \forall x\in\mathbb{R}:\quad X\le x \implies |\theta(x)-x| \le \varepsilon x$$

For every real $\varepsilon>0$ there is a real $X$ beyond which Chebyshev's function $\theta(x)=\sum_{p\le x}\log p$ differs from $x$ by at most $\varepsilon x$; this is the prime number theorem in the form $\theta(x)\sim x$. $\theta$ is Mathlib's `Chebyshev.theta`, defined for real $x$ as the sum of $\log p$ over primes $p\le x$, and $|\cdot|$ is the real absolute value.
