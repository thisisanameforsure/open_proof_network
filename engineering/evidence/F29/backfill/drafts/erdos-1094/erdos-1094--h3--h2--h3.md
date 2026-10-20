---
label: "ELS case A: k^(7/4) ≤ n ≪ k²/log k, a prime in (k/2, k)"
supersedes: null
drafted_with: Claude Fable 5.1 (claude-fable-5-1)
licence: CC-BY-4.0
---
$$\exists C, K_4\in\mathbb{N}\ \forall n,k\in\mathbb{N}:\quad K_4<k,\ \ k^{7/4}\le n,\ \ C\cdot n\cdot\lfloor\log_2 k\rfloor < k^2 \implies \exists\,p \text{ prime},\ \tfrac{k}{2}<p<k,\ \ p\mid\tbinom{n}{k}$$

There are constants $C$ and $K_4$ such that for all $k>K_4$ and all $n$ with $k^{7/4}\le n$ and $C\,n\lfloor\log_2 k\rfloor<k^2$ (that is, $n$ below a multiple of $k^2/\log k$), some prime $p$ with $k<2p$ and $p<k$ divides $\binom{n}{k}$. The first range hypothesis is a real inequality on the casts with the real exponent `(7 / 4 : ℝ)`; the second is in $\mathbb{N}$, where `Nat.log 2 k` is $\lfloor\log_2 k\rfloor$ (and $0$ for $k\le 1$), a natural number, so the right-hand side is a product of naturals.
