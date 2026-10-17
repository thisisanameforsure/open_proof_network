---
author: backfill
date: '2026-10-17'
drafted_with: Claude Fable 5.1 (claude-fable-5-1)
drafter: null
label: 'Euclid''s explicit bound: a prime in (n, n! + 1]'
licence: CC-BY-4.0
schema: gloss/v3
subject:
  kind: statement
  lean_hash: 4cb87a034e08ae9fe54f7fb38f498abe3247417df12fb7117340486e6629aa8f
  module: null
  node: variant-4cb87a03
supersedes: null
target: euclid-primes
---
$$\forall n\in\mathbb{N}\ \ \exists p\in\mathbb{N}:\quad n<p\ \wedge\ p\le n!+1\ \wedge\ p\ \text{prime}$$

For every natural number $n$ there is a prime $p$ with $n<p\le n!+1$, where $n!$ is Mathlib's `Nat.factorial`. Prime is the problem's own `Opn.IsPrime`: $2\le p$ and every $d$ with $p=d\cdot c$ for some natural $c$ is $1$ or $p$.
