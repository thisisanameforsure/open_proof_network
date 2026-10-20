---
kind: partial
node: erdos-1094--h2--h2--h2--h3--h1--h1
module: attempts/20261015T063320Z-opn-prove-aristotle-1015-partial.lean
drafted_with: Claude Fable 5.1 (claude-fable-5-1)
licence: CC-BY-4.0
---
Prove Konyagin's theorem by two reductions: the bound is trivial when 65536X ≥ 1, and a general scale λ reduces to λ/⌊λ⌋ in [1, 2) by splitting S into residue classes mod ⌊λ⌋.

The one hole is `core`: the theorem at a scale λ' in [1, 2) when 65536·X < 1. The assembly disposes of 65536·X ≥ 1 by |S| ≤ N + 1, and otherwise applies the hole to each residue class of S modulo q = ⌊λ⌋ on the function x ↦ g(c + qx), whose derivative bounds scale by q^r, and sums the q class bounds.
