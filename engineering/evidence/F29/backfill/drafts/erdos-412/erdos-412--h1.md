---
label: "Descent step for sigma orbits (gate-written form)"
supersedes: null
drafted_with: Claude Fable 5.1 (claude-fable-5-1)
licence: CC-BY-4.0
---
$$\forall m\ge 3:\quad \bigl(\neg\,\exists x,\ 2\le x<m\ \wedge\ \exists k,\ \sigma^{[k]}(x)=m\bigr)\ \Rightarrow\ \exists m',\ 2\le m'<m\ \wedge\ \exists i,j,\ \sigma^{[i]}(m)=\sigma^{[j]}(m')$$

For every natural number $m\ge 3$: if no $x$ with $2\le x<m$ reaches $m$ under some iterate of $\sigma$, then there is an $m'$ with $2\le m'<m$ whose forward $\sigma$-orbit meets that of $m$, that is, $\sigma^{[i]}(m)=\sigma^{[j]}(m')$ for some $i,j\ge 0$. Here $\sigma=\sigma_1$ is Mathlib's sum-of-divisors function on $\mathbb{N}$ (`ArithmeticFunction.sigma 1`, applied through its coercion `⇑(σ 1)`) and $\sigma^{[k]}$ its $k$-fold iterate; as written the file imports Mathlib without opening the `σ` notation's namespace, so the text names `σ` without that notation in scope.
