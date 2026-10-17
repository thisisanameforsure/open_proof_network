---
label: "Padé numerator coefficient closed form"
supersedes: 3d7d70d0952166b7bb4833cdb23245e9ad6a0a662e331c33d712eba1e1d1c95c
drafted_with: Claude Fable 5.1 (claude-fable-5-1)
licence: CC-BY-4.0
---
$$\forall k\le n:\quad \sum_{j=0}^{k}\frac{Q_c(n,j)}{2^{\,k-j}-1}\;=\;Q_c(n,k)\Bigl(\sum_{i=0}^{n-1}\frac{1}{1-2^{\,n+1+i-k}}-\sum_{b=0}^{k-1}\frac{2^{b+1}}{2^{b+1}-1}-\sum_{b=0}^{n-k-1}\frac{1}{1-2^{b+1}}\Bigr)+\sum_{b=0}^{n-k-1}\frac{Q_c(n,k+b+1)\,2^{b+1}}{2^{b+1}-1}$$

For any $Q_c:\mathbb{N}\times\mathbb{N}\to\mathbb{Q}$ fixed by hypothesis as $Q_c(n,k)=(-1)^k\,2^{k(k-1)/2}\prod_{i=0}^{k-1}\frac{2^{n-i}-1}{2^{i+1}-1}\prod_{i=0}^{n-1}\frac{2^{2n-k-i}-1}{2^{i+1}-1}$, and all natural numbers $k\le n$, the identity holds in $\mathbb{Q}$. Exponent subtractions are natural-number subtraction (none of $k-j$, $n+1+i-k$, $n-k$ truncates under $k\le n$) and $k(k-1)/2$ is natural-number division; on the left the term $j=k$ divides by $2^0-1=0$, which is $0$ in Lean, so the left side is in effect $p_k=\sum_{j<k}Q_c(n,j)/(2^{k-j}-1)$, and every denominator on the right is nonzero. The doc comment's 2-adic valuation claim is not part of the statement.
