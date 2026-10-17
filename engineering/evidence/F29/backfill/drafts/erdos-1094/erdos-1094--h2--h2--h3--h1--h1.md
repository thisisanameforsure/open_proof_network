---
label: "beyond van Doorn–Tang, n/gcd(n,k) prime, k ∤ n"
supersedes: null
drafted_with: Claude Fable 5.1 (claude-fable-5-1)
licence: CC-BY-4.0
---
$$\exists K\in\mathbb{N}\ \forall n,k\in\mathbb{N}:\quad 0<k,\ \ k^3\le n,\ \ \exp\!\Bigl(\frac{(\log k)^2}{20\log\log k}\Bigr)<n+1,\ \ k\lfloor n/k\rfloor\mid k!,\ \ \operatorname{minFac}\tbinom{n}{k}>\lfloor n/k\rfloor,\ \ \frac{n}{\gcd(n,k)}\text{ prime},\ \ k\nmid n\ \Longrightarrow\ k\le K$$

Only finitely many $k$ admit an $n$ with $n\ge k^3$ and $n+1>\exp\bigl((\log k)^2/(20\log\log k)\bigr)$ (natural logarithms, over the reals) such that $k\lfloor n/k\rfloor$ divides $k!$, the least prime factor of $\binom{n}{k}$ exceeds $\lfloor n/k\rfloor$, and $n/\gcd(n,k)$ is prime with $k\nmid n$. Lean conventions: `n / k` is floor division, $n/\gcd(n,k)$ is natural-number division, exact here since the gcd divides $n$, `Nat.minFac` is the least prime factor (1 at 1, 2 at 0), and `Real.log` is 0 at 0, so for small $k$ the exponent is a junk value ($\log\log 1=0$ and division by 0 gives 0).
