---
label: "Gaussian binomial at q = 2 is an integer"
supersedes: ae5860e243de7c5f3e242c67217f0988a4e88534662b88f43dcf39397fe8e323
drafted_with: Claude Fable 5.1 (claude-fable-5-1)
licence: CC-BY-4.0
---
$$\forall n,k\in\mathbb{N}\ \ \exists z\in\mathbb{Z}:\qquad z=\prod_{i=0}^{k-1}\frac{2^{\,n-i}-1}{2^{\,i+1}-1}$$

For all natural numbers $n$ and $k$ the product, computed in the rationals, is an integer (the Gaussian binomial coefficient $\binom{n}{k}_2$ in product form). The exponent $n-i$ is natural-number subtraction, which stops at $0$, so for $k>n$ the factor $i=n$ has numerator $2^0-1=0$ and the product is $0$; for $k=0$ the product is empty and equals $1$, and every denominator $2^{i+1}-1$ is at least $1$.
