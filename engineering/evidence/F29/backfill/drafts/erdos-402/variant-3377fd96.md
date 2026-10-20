---
label: "An element whose least prime factor is at least |A|"
supersedes: null
drafted_with: Claude Fable 5.1 (claude-fable-5-1)
licence: CC-BY-4.0
---
$$\forall A \subset \mathbb{N}\ \text{finite}:\ 0 \notin A \Rightarrow \forall x \in A,\ |A| \le \operatorname{minFac}(x) \Rightarrow \exists\, a, b \in A:\ \gcd(a,b) \le \frac{a}{|A|}$$

For a finite set A of positive integers and any x ∈ A whose least prime factor is at least |A|, there are a, b ∈ A (possibly equal) with gcd(a, b) ≤ a/|A|. minFac(x) is the least prime factor of x (minFac(1) = 1); the division is in ℚ.
