---
label: "Reduction to primitive sets"
supersedes: null
drafted_with: Claude Fable 5.1 (claude-fable-5-1)
licence: CC-BY-4.0
---
$$\Bigl(\forall B \subset \mathbb{N}\ \text{finite}:\ 0 \notin B,\ |B| = |A|,\ \gcd(B) = 1 \Rightarrow \exists\, a, b \in B:\ \gcd(a,b) \le \tfrac{a}{|B|}\Bigr) \Rightarrow \exists\, a, b \in A:\ \gcd(a,b) \le \frac{a}{|A|}$$

Assuming the Farey-structure claim as a hypothesis (for every finite A ⊂ ℕ with 0 ∉ A and every m, a ≤ m·gcd(a, b) for all a, b ∈ A implies that each pair has a·v = b·u for some coprime u, v with 1 ≤ u, v ≤ m): for every finite nonempty A ⊂ ℕ with 0 ∉ A, if the bound holds for every set B of the same size whose elements have greatest common divisor 1, then it holds for A. gcd(B) is the greatest common divisor of all elements of B, both divisions are in ℚ, and a and b may coincide.
