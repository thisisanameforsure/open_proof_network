$$\sum_{n=0}^{\infty} \frac{1}{(n+2)! - 1} \;=\; \sum_{m\ge 2} \frac{1}{m!-1} \;\notin\; \mathbb{Q}$$

The sum is taken in $\mathbb{R}$, with the index shifted so that it starts at $m = n + 2 = 2$; every denominator $m! - 1$ is at least $1$, so no division by zero occurs. `Irrational x` means that $x$ is not the image of any rational number. Lean's `∑'` would assign $0$ to a divergent series; this series converges (the proof of `erdos-68--h2` shows it), so the statement is about its actual value, $1 + \tfrac15 + \tfrac1{23} + \tfrac1{119} + \cdots \approx 1.2535$.

This is the affirmative answer to Erdős's question (erdosproblems.com/68): is $\sum_{n\ge 2} 1/(n!-1)$ irrational?
