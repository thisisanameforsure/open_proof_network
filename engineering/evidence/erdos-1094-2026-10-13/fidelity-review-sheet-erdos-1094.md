# Fidelity review sheet: erdos-1094 root

**For Mike.** You read this and decide whether the Lean says the conjecture. If you are satisfied, you record the next rung yourself. Nothing has been recorded on your behalf.

## 1. The Lean (`targets/erdos-1094/nodes/erdos-1094/Statement.lean`, imported from formal-conjectures at c7f31d5)

```lean
theorem Opn.erdos_1094 :
    {(n, k) : ℕ × ℕ | 0 < k ∧ 2 * k ≤ n ∧ (n.choose k).minFac > max (n / k) k}.Finite
```

The same, in standard notation:

$$\{(n,k)\in\mathbb N^2 : 0<k,\ 2k\le n,\ \operatorname{lpf}\tbinom nk>\max(\lfloor n/k\rfloor,k)\}\ \text{is finite.}$$

## 2. The conjecture as published

- **erdosproblems.com/1094**, read 2026-10-12: "For all $n\geq 2k$ the least prime factor of $\binom{n}{k}$ is $\leq \max(n/k,k)$, with only finitely many exceptions."
- **Erdős–Lacampagne–Selfridge, Acta Arith. 49 (1988)** list 14 exceptions: C(7,3), C(13,4), C(14,4), C(23,5), C(44,8), C(46,10), C(47,10), C(47,11), C(62,6), C(74,10), C(94,10), C(95,10), C(241,16), C(284,28).

## 3. Where Lean could differ from the words, and what each does here

| Point | Lean | Effect |
|---|---|---|
| Division | `n / k` is floor division | None. `minFac` is an integer, so `> ⌊n/k⌋` is the same as `> n/k`. |
| Least prime factor | `Nat.minFac`, with `minFac 1 = 1` and `minFac 0 = 2` | None. Here $n>k>0$, so $\binom nk\ge n\ge 2$. |
| `0 < k` | an added guard | Needed: without it every $(n,0)$ is in the set, since `minFac 1 = 1 > max 0 0`. The words implicitly mean $k\ge1$. |
| `2 * k ≤ n` | the words' $n\ge 2k$ | Matches. Without it, $(p,p-1)$ for every prime $p$ is an exception. |
| `max (n / k) k` | the words' $\max(n/k,k)$ | Matches, up to the floor (row 1). |
| `.Finite` | "only finitely many exceptions" | Matches. It is weaker than ELS's sharper claim that the exceptions are *exactly* their 14. |
| Order of pair | `(n, k)` | The symmetric $(n,n-k)$ is excluded by $2k\le n$ unless $n=2k$, as in the words. |

## 4. The exceptional set, computed

The Lean predicate's exceptional set was searched for every $k\le 1000$ with $n<k^3$, and for every $n$ when $k\le 26$ (method and code are in the numerical annex). The result is **exactly the 14 ELS pairs**, no more and no fewer. This was cross-checked against the literal predicate with Python's `math.comb` and the `minFac` conventions for $k\le 30$, $n\le 3000$.

The set is non-empty: a Lean `example` puts $(7,3)$ in it. It was checked on `POST /check`, which is a fast check, not the gate.

## 5. What to judge

1. Does the Lean in §1 say what §2 says, read with §3?
2. Is anything in §3 a meaning change you would not accept?
3. Does §4's exact match make you more confident than reading alone?

## 6. Recording it (your act)

- Today, `opn-gate fidelity erdos-1094 root screened-and-signed --graph … --by thisisanameforsure --evidence <file>` is refused with `pass-incomplete`. The QA pass is missing: erdos-1094 has no `qa/` directory.
- F26 (decisions v3.39, approved and not yet applied) rewrites that pass: the signer reads the mechanically rendered Lean beside its gloss. This sheet is built in that shape.
- So the rung can be recorded once F26-T0 lands, or after a QA pass under the current rules.
- The attestor may not be the statement's author. That author is The Formal Conjectures Authors, so you qualify.
