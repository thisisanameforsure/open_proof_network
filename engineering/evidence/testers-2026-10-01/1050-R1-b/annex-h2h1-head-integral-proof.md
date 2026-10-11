Annex to erdos-1050--h1-v2--h2--h1 (the numerator integrality of the Padé construction for sum 1/(2^n - 3)). A complete informal proof of the one part earlier annexes and logs left open (the "head" sum S1, called head_integral in the partial proofs), by partial fractions in the parameter c. Nothing here is checked in Lean; every identity below was checked in exact rational arithmetic for n = 1..13.

Notation. Fix n >= 1 and c = 8/3. D_k = prod over l in [1,n], l != k, of (1 - 2^(l-k)). A_k(x) = - prod_{t=1..n-1} (1 - x 2^(t+k)) / D_k, a polynomial in x of degree n-1. h_i(x) = 1/(1 - x 2^i). The node's right-hand side is 9^n (n-2)! P(n) M_n (S1 - S2), with P(n) = prod_{k=1..n} (1 - c 2^k), M_n = prod_{k=ceil(n/2)..n} (1 - 2^k), S1 = sum_{k=1..n} A_k(c) sum_{i=1..k} h_i(c), and S2 the sum with the factors 1/(2^i - 1). The S2 half is already proved in Lean (the partial submitted with this annex). This annex proves: 9^n P(n) M_n S1 is an integer (the factorial is not needed).

Step 0, a Lagrange fact (L). For distinct nodes y_1..y_n and every integer e >= -(n-1): sum_k y_k^e / prod_{l != k} (1 - y_l / y_k) = H_e(y_1..y_n), the complete homogeneous symmetric polynomial of degree e, read as 0 for e < 0. (Equivalently sum_k y_k^(e+n-1) / prod_{l != k} (y_k - y_l) = H_e: a divided difference of a monomial.) With y_k = 2^k this reads sum_k 2^(ke) / D_k = H_e, an integer. The recursion W(s, e) = W(s minus a, e-1) + y_a W(s, e-1), obtained from y_k^e = y_k^(e-1) (y_k - y_a) + y_a y_k^(e-1), proves integrality for integer nodes by induction.

Step 1, the identity. Write prod_{t=1..n-1} (1 - 2^t y) = sum_j alpha_j y^j (integer alpha_j), so A_k(x) = -(1/D_k) sum_j alpha_j 2^(kj) x^j. For each i and j: x^j h_i(x) = 2^(-ij) h_i(x) - sum_{s<j} 2^(-i(j-s)) x^s (a finite geometric sum in x 2^i). Summing over i <= k and then over k:

S1(x) = E(x) + sum_{i=1..n} b_i h_i(x), where
b_i = sum_{k=i..n} A_k(2^(-i)) = sum_{k=1..n} A_k(2^(-i)) (the terms k < i vanish, since the factor t = i-k of A_k(2^(-i)) is 1 - 2^0 = 0), and
E(x) = sum_{j=1..n-1} (2^j - 1)^(-1) sum_{j'=j..n-1} alpha_{j'} (H_{j'} - H_{j'-j}) x^(j'-j).
The formula for E uses sum_{i=1..k} 2^(-i m) = (1 - 2^(-k m)) / (2^m - 1) and then (L) twice (exponents j' and j'-m... all exponents that occur are >= -(n-1)). In words: E is the polynomial part of S1 at infinity and b_i the residues; the truncation i <= k of the harmonic-type sums costs nothing at the poles x = 2^(-i), because A_k vanishes there for k < i.

Step 2, integrality.
(a) E(c): each inner sum is an integer polynomial in x of degree <= n-2, so 3^(n-2) times it at x = 8/3 is an integer; each 2^j - 1 with 1 <= j <= n-1 divides M_n (take the multiple of j in [ceil(n/2), n]; this is `hdvd` in the Lean partial). So 3^(n-2) M_n E(c) is an integer.
(b) b_i is an integer. With y_k = 2^(k-i): b_i = - sum_k g(y_k) y_k^(n-1) / prod_{l != k} (y_k - y_l), g(y) = prod_{t=1..n-1} (1 - 2^t y), a divided difference of g(y) y^(n-1) over the n nodes. The nodes with k < i are the roots 2^(-t), t = 1..i-1, of g; cancelling them leaves the divided difference of the integer polynomial y^(n-1) prod_{t=i..n-1} (1 - 2^t y), times prod_{t=1..i-1} (-2^t), over the integer nodes 1, 2, ..., 2^(n-i). By (L) that is an integer. (Without the cancellation one only gets b_i in Z[1/2].)
(c) 3^n P(n) h_i(c) = 3 prod_{i' != i} (3 - 8 2^(i')) is an integer for i <= n.
Hence 9^n P(n) M_n S1(c) is an integer, and so is the node's expression (multiply by (n-2)!).

Relation to earlier notes on this target: the earlier logs split S1 by the weight k (a q-derivative, needing the q-lcm prod_{d<n} Phi_d(2)) and left a remainder R(n) open. Expanding at infinity instead of at 0 avoids the q-derivative term altogether: only the denominators 2^j - 1, j <= n-1, appear, which is exactly why the Mersenne block M_n is in the statement.

Suggested Lean route: (1) (L) as integrality of divided differences of monomials at integer nodes, by the recursion in Step 0; (2) the per-term identity for x^j h_i; (3) assemble. The existing partial's `key` step is the special case of (L) used for S2.
