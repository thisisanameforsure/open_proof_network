# B: published results that could serve as holes of an erdos-849 skeleton (21:25Z)

All checked against the source on 2026-10-26 (arXiv / Integers / Crossref). "Known" = published proof, not in Lean.
N(a) below counts solutions (n,k) of C(n,k)=a in the full triangle; rows(a) = the root's count (half triangle, 1 ≤ k ≤ n/2).

## Negative direction (refute root): enough to show rows(a) ≤ B for all a (then t = B+1 fails).
This is Singmaster's conjecture (open; my variant-3969f1f7, PR #995, states it with relation proof → ¬root).
A natural region split, each piece a hole:

R1. k = 1: exactly one row (n = a). Elementary.
R2. Interior: exp((log n)^{2/3+ε}) ≤ k ≤ n/2.  KNOWN.
    Matomäki–Radziwiłł–Shao–Tao–Teräväinen, "Singmaster's conjecture in the interior of Pascal's triangle",
    Quart. J. Math. 73 (2022) 1137–1177, arXiv:2106.03335, **Theorem 1.3**: for ε > 0 and t sufficiently large
    (depending on ε), at most TWO solutions (n,m) of C(n,m)=t with exp(log^{2/3+ε} n) ≤ m ≤ n/2.
    Same theorem: at most one solution in the narrower range up to n/exp(log^{1−ε'} n). Remark 1.11: exactly three
    interior solutions impossible. Remark 1.7: bounds effective but unoptimised (useless numerically).
R3. Small k: 2 ≤ k ≤ exp((log n)^{2/3+ε}).  OPEN — this is the hole that carries the whole difficulty.
    Conditional: MRSTT Remark 1.5: assuming de Weger's conjecture, at most one solution in this region for large t.
    Partial knowledge: for each fixed pair (k,l) the collision equation C(n,k)=C(m,l) is solved (finitely many) for
    (2,3) Avanesov, Acta Arith. 12 (1966) 409–420; (2,4) Pintér, Publ. Math. Debrecen 47 (1995) 411–415, de Weger,
    Quart. J. Math. Oxford (2) 47 (1996) 221–231; (2,5) Bugeaud–Mignotte–Siksek–Stoll–Tengely, Algebra & Number
    Theory 2 (2008) 859–885; (2,6),(2,8),(3,6),(4,6),(4,8) Stroeker–de Weger, Math. Comp. 68 (1999) 1257–1281;
    (3,4) Mordell, Pacific J. Math. 13 (1963) 1347–1351 (all as listed in BBdW proof of Thm 2.2). Siegel gives
    finiteness for each fixed (k,l) ineffectively. None bounds the number of k's at once, so these do not close R3.
R4. Small a (a < t0 of R2): finitely many a, each rows(a) ≤ a (C's spec-38faff03: rows ⊆ [2,a]). Elementary,
    but t0 is ineffective/huge, so the assembly needs only "finite set of a ⇒ bounded", not a computation.
Assembly: rows(a) ≤ 1 (R1) + R3-bound + 2 (R2) for a ≥ t0; ≤ max over a < t0 otherwise. Fully provable once
holes are stated; R2 is a known theorem (formalising it is out of reach today), R3 is open.

Unconditional global bounds (not enough alone, since they grow):
- Singmaster, Amer. Math. Monthly 78(4) (1971) 385–386: N(a) = O(log a). (C's variant-a30f5217: rows ≤ log2 a.)
- Abbott–Erdős–Hanson, Amer. Math. Monthly 81(3) (1974) 256–261: N(a) = O(log a / log log a); Thm 1: average and
  normal order of N is 2.
- Kane, Integers 7 (2007) #A53: N(t) = O(log t · log log log t / (log log t)^3).
- MRSTT Remark 1.6: AEH give O(log^{3/4} t) solutions for n^{5/6} ≤ m ≤ n/2; Kane's arguments give
  O_ε(log t / (log log log t)^3) for exp(log^{1/2+ε} n) ≤ m ≤ n^{5/6}.

Search evidence (for testing holes): Blokhuis–Brouwer–de Weger, Integers 17 (2017) #A64, arXiv:1707.06893,
**Theorem 2.2**: no collisions beyond the known list for n ≤ 10^6 and for C(n,k) ≤ 10^60. **Conjecture 2.1**
(de Weger 1997): the known list (3003 double; 120, 210, 1540, 7140, 11628, 24310; Lind family) is all.
My own exact search (B/collide.c, running): pairs with some k ≥ 4 to 10^37, the (2,3) pair to 10^28.
Under Conj 2.1, rows(a) ≤ 4 for all a — so the negative answer is "expected", and t = 5 is the first failing t.

## Affirmative direction (the root as stated): no published result produces a with exactly t rows for t ≥ 5.
Lind, Fibonacci Quart. 6(3) (1968) 86ff; Singmaster, Fibonacci Quart. 13(4) (1975) 295–298: infinitely many a in
≥ 3 rows (C(F_{2i+2}F_{2i+3}, F_{2i}F_{2i+3}) = C(F_{2i+2}F_{2i+3}−1, F_{2i}F_{2i+3}+1)). Tovey, Fibonacci Quart.
23 (1985) 356–358 and Stroeker–de Weger, Acta Arith. 87 (1999) 339–365 classify collisions of adjacent shapes
(m,l) = (n−1,k+1), (n−1,k+2), (n−2,k+1). Any affirmative skeleton would have a hole contradicting de Weger's
conjecture; I know of no published route.
