# Erdős 412: a descent reduction, and where the difficulty actually sits

Node: `erdos-412` — for all m, n ≥ 2 there are i, j with σ_i(m) = σ_j(n), where σ_1 = σ is the
sum-of-divisors function and σ_k = σ ∘ σ_{k-1}.

Write **x ~ y** for "the forward σ-orbits of x and y meet", i.e. ∃ i j, σ^i(x) = σ^j(y). The node
says exactly that ~ holds for every pair of integers ≥ 2.

## 1. ~ is an equivalence relation on the integers ≥ 2

Reflexivity is i = j = 0 and symmetry is swapping the two indices. Transitivity is where the
forward determinism of the orbit is used: if σ^a(x) = σ^b(y) and σ^c(y) = σ^d(z), then

    σ^(c+a)(x) = σ^c(σ^a(x)) = σ^c(σ^b(y)) = σ^b(σ^c(y)) = σ^b(σ^d(z)) = σ^(b+d)(z),

so x ~ z. Consequently the statement is equivalent to the one-variable statement **m ~ 2 for
every m ≥ 2**: the pairwise claim follows by symmetry and transitivity through the single
reference point 2.

## 2. Descent

By strong induction on m, "m ~ 2 for all m ≥ 2" follows from a descent principle:

    (D) every m ≥ 3 satisfies m ~ m' for some m' with 2 ≤ m' < m.

## 3. What descent gives away for free

If m lies on the orbit of a smaller start — m = σ^k(x) with 2 ≤ x < m — then m ~ x holds by
definition of ~, with (i, j) = (0, k), and the induction hypothesis applies to x. In particular
this covers every m = σ(p) = p + 1 with p prime (σ(p) = 1 + p), and more generally every value
of σ taken below m. Of the 238 integers 3 ≤ m ≤ 240, 88 are of this kind.

So the only m that need an argument are the **orbit-minimal** ones: those no smaller starting
point flows into. That is the hypothesis carried by the hole in the skeleton.

## 4. The hole

    ∀ m ≥ 3, (¬ ∃ x, 2 ≤ x ∧ x < m ∧ ∃ k, σ^k(x) = m) →
        ∃ m', 2 ≤ m' ∧ m' < m ∧ ∃ i j, σ^i(m) = σ^j(m')

## 5. What a search says about the hole

Orbits were computed for every 2 ≤ m ≤ 240 to 25 σ-steps (values up to ~10^12) and intersected
pairwise. Of the 150 orbit-minimal m in that range, 128 do have a descent partner visible
within 25 steps — the merge is a finite, exhibitable fact for each of them. The first few:

| m | partner m' | i | j | common value σ^i(m) = σ^j(m') |
|---|---|---|---|---|
| 9 | 2 | 3 | 6 | 24 |
| 10 | 5 | 3 | 4 | 56 |
| 11 | 5 | 1 | 2 | 12 |
| 17 | 5 | 3 | 4 | 56 |
| 21 | 16 | 1 | 2 | 32 |
| 22 | 2 | 5 | 9 | 480 |
| 23 | 2 | 1 | 6 | 24 |
| 25 | 16 | 1 | 1 | 31 |
| 26 | 19 | 1 | 2 | 42 |
| 34 | 5 | 2 | 5 | 120 |
| 35 | 33 | 1 | 1 | 48 |
| 37 | 2 | 2 | 7 | 60 |
| 41 | 19 | 1 | 2 | 42 |
| 43 | 33 | 3 | 3 | 224 |

The residue — orbit-minimal m for which **no** partner was found within 25 steps — is

    5, 16, 19, 27, 29, 33, 49, 50, 52, 66, 81, 85, 105, 146, 147, 163, 170, 189, 197, 199, 218, 226

led by m = 5, whose orbit (5, 6, 12, 28, 56, 120, 360, 1170, 3276, 10192, 24738, 61440, ...)
has not been seen to meet the orbit of 2 (2, 3, 4, 7, 8, 15, 24, 60, 168, 480, 1512, 4800, ...);
after 25 steps both are past 10^11 and still disjoint. Whether 2 ~ 5 holds is the usual test case
for this conjecture, and the skeleton isolates it: 5 is the smallest m the hole must handle.

## 6. Honest assessment of what this skeleton is worth

It is a reduction of shape, not of depth. Given §1–§3 the hole and the conjecture imply each
other, so nothing here makes the problem smaller in the logical sense. What it does buy:

- the two-variable statement becomes a one-variable one, against a fixed reference point;
- everything downstream of a smaller start — a third of the small cases, and every p + 1 for p
  prime — is discharged mechanically, inside the kernel-checked assembly, not by hand;
- the remaining obligation is per-m and exhibitable: for a given m one produces a partner m' and
  a pair (i, j), which is exactly what a search for merges produces. For 3 ≤ m ≤ 240 that leaves
  22 genuinely open values rather than 238.

The mathematics that would close the hole is not present here, and no claim is made that it is
within reach. The value offered is the frame plus the list of 22 residual m.

Computation: sum-of-divisors by Pollard-rho factorisation, 25 iterations, 2 ≤ m ≤ 240; it is
reproducible from this description in a few lines and is not part of the kernel-checked artifact.
