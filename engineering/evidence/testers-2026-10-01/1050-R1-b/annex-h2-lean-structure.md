Annex to erdos-1050--h1-v2--h2 (integrality of the Padé numerators and denominators for sum 1/(2^n - 3)). How the sorry-free Lean proof submitted on this node is organised, for readers and for anyone reusing its lemmas. The mathematics of the numerator half is in annex a03db62f0576f792454c3f95d14fb02d193662242ec562819da63116009d326b on the child node erdos-1050--h1-v2--h2--h1; the partial-fraction and residue steps (hpf, hres) are unchanged from the earlier partial on this node (annexes 959e0d5b... and ab20b788...).

Notation: for a finite set s of naturals and k in s, Pi(s,k) = prod over l in s minus k of (1 - 2^(l-k)); with s = {1..n} this is the denominator D_k of the Padé coefficients A_k.

Shared lemmas, stated once at the top of the proof (all over the reals, nodes 2^k):

1. h0: for nonempty s, sum_{k in s} 1/Pi(s,k) = 1. This is Mathlib's Lagrange.sum_basis for the nodes 2^(-k), evaluated at 0.
2. hrec: for a in s and any weight f, sum_{k in s} 2^k f(k)/Pi(s,k) = sum_{k in s minus a} 2^k f(k)/Pi(s minus a,k) + 2^a sum_{k in s} f(k)/Pi(s,k). (Split off the factor l = a of each product; one line of algebra per term.)
3. hW: sum_{k in s} (2^k)^e / Pi(s,k) is an integer for every e >= 0 (it is the complete homogeneous symmetric polynomial h_e of the nodes). Induction on |s| + e with hrec, base cases h0 and the empty set.
4. hV: sum_{k in s} (2^k)^(-m) / Pi(s,k) = 0 for 1 <= m < |s|. Induction on m with hrec and h0.
5. hpoly: prod_{t=1..n-1} (1 - 2^t y) = sum_{j<n} alpha_j y^j with integer alpha_j (coefficients of an integer polynomial of degree < n).
6. hgeo: sum_{i=1..k} 2^(-im) = (1 - 2^(-km))/(2^m - 1); hdvd: 2^i - 1 divides prod_{k=ceil(n/2)..n} (1 - 2^k) for 1 <= i <= n-1.

What each integrality statement then costs:

- Denominator (hden): 3^(n-1) sum_k A_k = - sum_j alpha_j 3^(n-1-j) 8^j h_j, by hpoly and hW. This replaces the earlier 120-line argument through coefficients of a product of geometric series.
- The tail sums of the numerator (S2; `key`): 3^(n-1-i) sum_k A_k (c 2^k)^(-i) = - sum_{j>=i} alpha_j 3^(n-1-j) 8^(j-i) h_(j-i); the terms j < i vanish by hV. Same replacement.
- The head sum of the numerator (S1): residue_integral (the residues b_i are integers: each term is a product of two Gaussian binomials times a power of 2, proved by the q-Pascal induction hG) and polypart_integral (S1 minus its principal parts is sum_{s<j} alpha_j c^s (h_j - h_s)/(2^(j-s) - 1), by hgeo and hW, cleared by 3^n and the Mersenne block via hdvd).

Sizes: the proof of the child node alone is 565 lines, 117487 heartbeats; the direct proof of this node is 848 lines, 164220 heartbeats (cap 200000). With the earlier coefficient argument kept, either one exceeded the cap, which is why the two key steps were rewritten on top of hW and hV rather than left as they were.

Not needed anywhere: the factorial (n-2)! in the statement (the proof multiplies by it at the end), and any q-lcm or cyclotomic argument.
