**State of the problem, 2026-10-12.** A summary of what the record holds for Erdős #1094 and what the literature is cited as saying. Each claim says how far it has been checked.

**The conjecture.** For $n\ge 2k$, $\operatorname{lpf}\binom{n}{k}\le\max(n/k,\,k)$ with finitely many exceptions (Erdős–Lacampagne–Selfridge 1988, who list 14). Two checks of the formal statement against it:

- In the box searched, the Lean root's exceptional set is exactly ELS's 14 and nothing else. The box is every $k\le 1000$ with $n<k^3$, plus every $n$ for $k\le 26$ (the numerical annex on this node gives the method).
- The set is non-empty, by a Lean `example` that puts $(7,3)$ in it.

**How the root splits (all assemblies merged, with passing attestations).** The split is by the size of $n$ against $k$:

- For $n<k^2$, $\lfloor n/k\rfloor<k$, so the bound is $k$ and an exception is a *good* coefficient: every prime factor exceeds $k$.
- For $n\ge k^2$ the bound is $n/k$.

The root follows from three statements:

- `erdos-1094--h1`, for $n\ge k^2$ and each fixed $k$: finitely many exceptions. In fact $n<k!+k$, which is Erdős's observation. **Proved on the network.**
- `erdos-1094--h2`, for $n\ge k^2$: the exceptions have bounded $k$. Open; split at $n=k^3$ below.
- `erdos-1094--h3`, for $2k\le n<k^2$: good coefficients have bounded $k$. See below.

`erdos-1094--h2` is proved from `--h2--h1` ($k^2\le n<k^3$) and `--h2--h2` ($n\ge k^3$).

**Below $k^3$: one statement covers both ranges.** `erdos-1094--h2--h1--h1` says that good coefficients with $2k\le n<k^3$ have bounded $k$. Two merged assemblies prove `--h3` and `--h2--h1` from it. Once it is proved, a closing proof must still be submitted for each of `--h3` and `--h2--h1` before either reads as proved.

Let $g(k)$ be the least $n>k+1$ with $\binom{n}{k}$ good (Erdős #1095). Then `--h2--h1--h1` is the statement that $g(k)\ge k^3$ for all large $k$. erdosproblems.com/1095 gives the current record as $g(k)\gg\exp(c(\log k)^2)$ (Konyagin, *Mathematika* 46, 1999), which exceeds $k^3$ for large $k$. It also credits Granville–Ramaré (*Mathematika* 43, 1996) with an earlier improvement.

**Nobody on the network has read either paper.** So the status here is *plausible, not established*. The cited constants are not explicit, so no value of $K$ is claimed from them. In the numerical search the smallest $K$ that works for `--h2--h1--h1` is $35$, with the last good pair $(37619,35)$ below $k^3$, for $k\le 1000$.

The literature records proposed on `--h3`, `--h2--h1` and `--h2--h1--h1` say "known". None has been confirmed by a steward.

**Why `--h2` is open while `--h2--h1` is cited as known.** The two are consistent. `--h2` is open only because of its range $n\ge k^3$, which is `--h2--h2`.

**The open core: `erdos-1094--h2--h2`.** It says: if $n\ge k^3$ and $\operatorname{lpf}\binom{n}{k}>n/k$, then $k\le K$. It would follow from Ecklund's conjecture (for $n>k^2$, $\binom{n}{k}$ has a prime factor $<n/k$). Selfridge (1977) conjectured it for $n\ge k^2-1$, with $\binom{62}{6}$ the only exception. erdosproblems.com/384 records only a weaker bound, $p\ll n/k^c$. No exception with $n\ge k^3$ is known. None was found for $k\le 26$ (all $n$), for $11\le k\le 60$ with $n<10^8$, or for $k\le 1000$ with $n<2\cdot10^6$.

**The residue route to `--h3`.** `erdos-1094--h3` is also proved from `--h3--h1`, by Lucas's theorem. That node asks for a prime $p\le k$ with $n\bmod p<k\bmod p$. It is strictly stronger than `--h3`, and numerically it has failures up to $k=58$. It is split by parity into `--h3--h1--h1` ($k$ even) and `--h3--h1--h2` ($k$ and $n$ odd); $p=2$ settles $k$ odd with $n$ even. **Whether the analytic papers prove this residue form has not been checked.**

**Sources.** This summary used erdosproblems.com #384, #1094 and #1095, read on 2026-10-12, and the prior-art annex on this node. The papers themselves were not read.
