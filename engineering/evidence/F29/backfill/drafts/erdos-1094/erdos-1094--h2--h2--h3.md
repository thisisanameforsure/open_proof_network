---
label: "beyond van Doorn–Tang's range, n ≥ k³"
supersedes: edf65ce8e9815c5a2ef3cc9fbe1cf5a61a3075b2350893c3c60deea4cec9844c
drafted_with: Claude Fable 5.1 (claude-fable-5-1)
licence: CC-BY-4.0
---
$$\exists K\in\mathbb N\ \forall n,k\in\mathbb N:\ 0<k,\ k^3\le n,\ \exp\!\Bigl(\frac{(\log k)^2}{20\,\log\log k}\Bigr)<n+1,\ k\lfloor n/k\rfloor \mid k!,\ \operatorname{minFac}\binom nk>\lfloor n/k\rfloor\ \Longrightarrow\ k\le K.$$

In words: only finitely many $k$ admit an $n\ge k^3$ with $n+1>\exp(\log^2 k/(20\log\log k))$ (natural logarithms, over the reals) such that $k\cdot\lfloor n/k\rfloor$ divides $k!$ and the least prime factor of $\binom nk$ exceeds $\lfloor n/k\rfloor$.

Lean conventions: `n / k` is floor division; `Real.log` is 0 at 0 and takes $\log|x|$ for negative $x$, so for small $k$ the exponent is a junk value ($\log\log 1 = 0$ and division by 0 gives 0 in Lean); `Nat.minFac` is 1 at 1; `0 < k` is a hypothesis.
