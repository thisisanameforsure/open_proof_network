---
label: "Pair or a prime factor p with |B| ≤ 3p"
supersedes: null
drafted_with: Claude Fable 5.1 (claude-fable-5-1)
licence: CC-BY-4.0
---
$$\begin{aligned}&0 \notin B,\ B \ne \emptyset,\ \gcd(B) = 1,\ |B|\ \text{not prime},\ |B| \ne q + 1\ \text{for every prime } q,\\&\forall a, b \in B:\ a \le |B| \cdot \gcd(a,b),\qquad \forall a \in B,\ \forall p\ \text{prime},\ \forall k \in \mathbb{N}:\ p^k \mid a \Rightarrow p^k < |B|\\&\Longrightarrow\ \bigl(\exists\, a, b \in B:\ \gcd(a,b) \le \frac{a}{|B|}\bigr) \vee \bigl(\exists\, p\ \text{prime}:\ |B| \le 3p,\ \exists\, a \in B,\ p \mid a\bigr)\end{aligned}$$

For every finite set B of positive integers (0 ∉ B, B nonempty) whose elements have greatest common divisor 1, whose size |B| is neither a prime nor one more than a prime, in which a ≤ |B|·gcd(a, b) for all a, b ∈ B, and in which every prime power dividing an element is below |B|, either some a, b ∈ B (possibly equal) have gcd(a, b) ≤ a/|B|, or some element of B has a prime factor p with |B| ≤ 3p. gcd(B) is the greatest common divisor of all elements of B; the division is in ℚ, the rest is over ℕ.
