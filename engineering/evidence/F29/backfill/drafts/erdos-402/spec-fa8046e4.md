---
label: "Graham's bound for size n from a colouring certificate"
supersedes: null
drafted_with: Claude Fable 5.1 (claude-fable-5-1)
licence: CC-BY-4.0
---
$$\begin{aligned}&n \ge 2,\ L > 0,\ S \subset \mathbb{N}\ \text{finite},\ c : \mathbb{N} \to \mathbb{N},\\&\forall k < n,\ \forall j < k,\ j > 0:\ k \mid L j\ \wedge\ L j / k \in S,\qquad \forall a \in S:\ c(a) + 2 < n,\\&\forall a, b \in S,\ a \ne b,\ c(a) = c(b):\ n \cdot \gcd(a,b) \le a\ \vee\ n \cdot \gcd(a,b) \le b\\&\Longrightarrow\ \forall A \subset \mathbb{N}\ \text{finite}:\ 0 \notin A,\ |A| = n \Rightarrow \exists\, a, b \in A:\ \gcd(a,b) \le \frac{a}{|A|}\end{aligned}$$

Given n ≥ 2, a positive L, a finite set S ⊂ ℕ and a colouring c such that every L·j/k with 0 < j < k < n is an integer lying in S, every colour c(a) of an element of S is below n − 2, and two distinct elements of S of the same colour a, b satisfy n·gcd(a, b) ≤ a or n·gcd(a, b) ≤ b: every set A of exactly n positive integers has a, b ∈ A (possibly equal) with gcd(a, b) ≤ a/|A|. L·j/k is natural-number division, exact because k divides L·j; the last division is in ℚ.
