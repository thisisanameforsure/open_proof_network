---
label: "Irrationality of the tail sum T"
supersedes: 7017463d4f4241b806e5c2cd8c3a3bd1a547993f808899ad641884c200038f19
drafted_with: Claude Fable 5.1 (claude-fable-5-1)
licence: CC-BY-4.0
---
$$T=\sum_{n=0}^{\infty}\frac{1}{2^{n+3}-3}=\frac15+\frac1{13}+\frac1{29}+\frac1{61}+\cdots\ \notin\ \mathbb{Q}$$

The real number $T$ is irrational (Mathlib's `Irrational`): it is not equal to any rational number. The sum is Lean's unconditional `∑'` over all natural numbers $n\ge 0$, computed in $\mathbb{R}$, which Lean gives the value $0$ when the family is not summable; the statement has no hypotheses and does not assert summability separately.
