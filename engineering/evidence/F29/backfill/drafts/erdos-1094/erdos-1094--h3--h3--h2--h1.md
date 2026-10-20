---
label: "GR Lemma 5.1: {n/p} below σ carries weight σ Σ log p + o(k)"
supersedes: null
drafted_with: Claude Fable 5.1 (claude-fable-5-1)
licence: CC-BY-4.0
---
$$\forall C\in\mathbb{N},\ \delta>0\ \exists K_5\ \forall n,k\in\mathbb{N},\ K_5<k,\ k^2\le C n\lfloor\log_2 k\rfloor,\ n<k^2,\ \forall \sigma\in[0,1]:\quad \Bigl|\sum_{\substack{p \text{ prime}\\ k/2<p<11k/20}}\ [\{n/p\}<\sigma]\,\log p \;-\; \sigma \sum_{\substack{p \text{ prime}\\ k/2<p<11k/20}} \log p\Bigr| \le \delta k$$

For every constant $C$ and real $\delta>0$ there is a threshold $K_5$ such that for all $k>K_5$, all $n<k^2$ with $k^2\le C\,n\lfloor\log_2 k\rfloor$, and every real $\sigma\in[0,1]$, the $\log p$-weighted count of primes $p$ with $k<2p$ and $20p<11k$ whose fractional part $\{n/p\}$ is below $\sigma$ differs from $\sigma$ times the total weight $\sum\log p$ over the same primes by at most $\delta k$. $[\{n/p\}<\sigma]$ stands for Lean's `if Int.fract (n / p) < σ then Real.log p else 0` with the quotient taken in $\mathbb{R}$; both sums run over `Finset.range k` filtered by the three conditions, and the range hypotheses are in $\mathbb{N}$ where `Nat.log 2 k` is $\lfloor\log_2 k\rfloor$ (and $0$ for $k\le 1$), a natural number, so the right-hand side is a product of naturals.
