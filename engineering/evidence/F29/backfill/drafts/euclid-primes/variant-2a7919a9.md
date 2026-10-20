---
label: "No finite list contains all the primes"
supersedes: null
drafted_with: Claude Fable 5.1 (claude-fable-5-1)
licence: CC-BY-4.0
---
$$\forall\, l\in\operatorname{List}(\mathbb{N})\ \ \exists p\in\mathbb{N}:\quad p\ \text{prime}\ \wedge\ p\notin l$$

For every list of natural numbers there is a prime that is not a member of it (Euclid, Elements IX.20). Prime is the problem's own `Opn.IsPrime`: $2\le p$ and every $d$ with $p=d\cdot c$ for some natural $c$ is $1$ or $p$.
