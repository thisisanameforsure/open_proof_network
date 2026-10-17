---
label: "Granville–Ramaré: a carry at some prime p in (k/2, 11k/20)"
supersedes: null
drafted_with: Claude Fable 5.1 (claude-fable-5-1)
licence: CC-BY-4.0
---
$$\forall C\in\mathbb{N}\ \exists K_2\ \forall n,k\in\mathbb{N}:\quad K_2<k,\ \ k^2\le C\cdot n\cdot\lfloor\log_2 k\rfloor,\ \ n<k^2 \implies \exists\,p \text{ prime},\ \tfrac{k}{2}<p<\tfrac{11k}{20},\ \ n \bmod p < k \bmod p$$

For every constant $C$ there is a threshold $K_2$ such that for all $k>K_2$ and all $n<k^2$ with $k^2\le C\,n\lfloor\log_2 k\rfloor$ (the range $n\gg k^2/\log k$ that the ELS bound leaves), some prime $p$ with $k<2p$ and $20p<11k$ has $n \bmod p<k \bmod p$, a carry at the last base-$p$ digit. Everything is in $\mathbb{N}$: `Nat.log 2 k` is $\lfloor\log_2 k\rfloor$ (and $0$ for $k\le 1$), a natural number, so the right-hand side is a product of naturals, and `n % p` is the least non-negative residue.
