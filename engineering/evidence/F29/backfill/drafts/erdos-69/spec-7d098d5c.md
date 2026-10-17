---
label: Mertens' second theorem, bounded-error form
supersedes: null
drafted_with: Claude Fable 5.1 (claude-fable-5-1)
licence: CC-BY-4.0
---
$$\exists C\ge 0\ \ \forall x\in\mathbb{N},\ x\ge 2:\quad \Bigl\lvert \sum_{p\le x,\ p\ \text{prime}}\frac{1}{p} - \log\log x \Bigr\rvert \le C$$

There is a nonnegative real C such that for every natural x ≥ 2 the sum of 1/p over the primes p ≤ x differs from log log x by at most C, with log the natural logarithm (Mathlib's `Real.log`) and the primes p ≤ x the finset `Nat.primesLE x`.
