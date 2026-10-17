---
label: "Euclid's explicit bound: a prime in (n, n! + 1]"
supersedes: null
drafted_with: Claude Fable 5.1 (claude-fable-5-1)
licence: CC-BY-4.0
---
$$\forall n\in\mathbb{N}\ \ \exists p\in\mathbb{N}:\quad n<p\ \wedge\ p\le n!+1\ \wedge\ p\ \text{prime}$$

For every natural number $n$ there is a prime $p$ with $n<p\le n!+1$, where $n!$ is Mathlib's `Nat.factorial`. Prime is the problem's own `Opn.IsPrime`: $2\le p$ and every $d$ with $p=d\cdot c$ for some natural $c$ is $1$ or $p$.
