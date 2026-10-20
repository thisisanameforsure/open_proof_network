"""Deeper statistics: the carry-parity rule, conditional selection, block tests, close calls, plots."""
from __future__ import annotations

import sys
from collections import Counter

import numpy as np

sys.path.insert(0, ".")
from analyze import gap_stats, discrepancy, autocorr, residues, control  # noqa: E402


def load(path):
    d = np.load(path)
    return d["A"], d["c"], d["dev"], d["sel"], d["flags"], d["cnt"]


def dcount_before(A, N):
    """D_<(m) = #{a in A, a < m : a | m}  (excludes m itself)."""
    cntA = np.zeros(N + 1, dtype=np.int32)
    for a in A:
        cntA[2 * a :: a] += 1
    return cntA


def parity_rule(A, c, cnt, sel, N):
    """Check m+1 in A  <=>  (D_<(m+1) + carry_in(m+1)) even, where carry_in = c_m - 1 ... derive from data:
    u_m = c_m - f_m, f_m = D_<(m+1)/2 + g, selection iff frac(f_m) < 1/2 (up to the 2^-m edge)."""
    ind = np.zeros(N + 2, dtype=bool)
    ind[A] = True
    Dlt = dcount_before(A, N + 1)
    m = np.arange(1, N)            # decide m+1 from state at m
    cm = c[m]                      # c_m
    s = ind[m + 1]
    # c_m = ceil(f_m); with f_m = D/2 + g: parity of (c_m - 1) ... test the claim:
    # selection iff D_<(m+1) + floor(2 g) is even, where floor(2g) is the carry from positions >= m+2 into m+1.
    # We cannot read g directly here, but floor(f_m) = c_m - 1, and floor(f_m) = floor(D/2 + g).
    # Equivalent test: selection iff (c_m - 1 - D_<(m+1)) ... instead verify the cleaner identity
    #   selection iff  2*(c_m - 1) - D_<(m+1) - floor(2g) == 0  cannot be done without g, so verify numerically that
    #   P(sel | D_<(m+1) parity, c_m) splits cleanly.
    D = Dlt[m + 1]
    print("\nselection vs D_<(m+1) (number of earlier elements dividing m+1):")
    print("  d   n        P(m+1 in A)")
    for d in range(0, 16):
        mask = D == d
        if mask.sum() > 50:
            print(f"  {d:2d} {mask.sum():8d}   {s[mask].mean():.4f}")
    print("  parity of D_<:  even", f"{s[D % 2 == 0].mean():.4f}", " odd", f"{s[D % 2 == 1].mean():.4f}")
    print("\nselection vs carry c_m (carry into position m from the right is c_m - 1):")
    for cv in range(1, 30):
        mask = cm == cv
        if mask.sum() > 50:
            print(f"  c_m={cv:2d} n={mask.sum():8d}  P={s[mask].mean():.4f}   even-D {s[mask & (D%2==0)].mean():.4f}  odd-D {s[mask & (D%2==1)].mean():.4f}")
    return Dlt


def special_numbers(A, N, Dlt):
    ind = np.zeros(N + 1, dtype=bool)
    ind[A] = True
    # primes
    sieve = np.ones(N + 1, dtype=bool)
    sieve[:2] = False
    for i in range(2, int(N**0.5) + 1):
        if sieve[i]:
            sieve[i * i :: i] = False
    primes = np.flatnonzero(sieve)
    print(f"\nprimes: {ind[primes].mean():.4f} of {len(primes)} primes are in A (D_< = 0 for all)")
    pw = 2 ** np.arange(1, int(np.log2(N)) + 1)
    print("powers of two in A:", [int(p) for p in pw if ind[p]], " not:", [int(p) for p in pw if not ind[p]])
    print("first 40 non-elements:", np.flatnonzero(~ind[1:])[:40] + 1)
    # P(m in A) by number of divisors of m (all divisors, not just in A)
    tau = np.zeros(N + 1, dtype=np.int32)
    for d in range(1, N + 1):
        tau[d::d] += 1
    print("P(m in A) by tau(m):")
    for t in [2, 3, 4, 6, 8, 12, 16, 24, 32, 48, 64, 96]:
        mask = tau[1:] == t
        if mask.sum() > 30:
            print(f"  tau={t:3d}  n={mask.sum():7d}  P={ind[1:][mask].mean():.4f}")
    # 2a, 3a conditional
    for k in [2, 3, 4, 5, 6, 8, 12]:
        a = A[A * k <= N]
        print(f"  P(k*a in A | a in A), k={k:2d}: {ind[a*k].mean():.4f}  n={len(a)}   P(k*b in A | b not in A): ", end="")
        b = np.flatnonzero(~ind[1:]) + 1
        b = b[b * k <= N]
        print(f"{ind[b*k].mean():.4f}")


def block_test(A, N, kmax=16):
    ind = np.zeros(N + 1, dtype=np.uint8)
    ind[A] = 1
    x = ind[1:]
    print("\nk-bit block chi-square (p-value under the fair-coin model):")
    from scipy.stats import chi2
    for k in range(1, kmax + 1):
        # non-overlapping blocks
        nb = len(x) // k
        blocks = x[: nb * k].reshape(nb, k)
        vals = blocks @ (1 << np.arange(k - 1, -1, -1)).astype(np.int64)
        counts = np.bincount(vals, minlength=1 << k)
        exp = nb / (1 << k)
        stat = ((counts - exp) ** 2 / exp).sum()
        df = (1 << k) - 1
        p = chi2.sf(stat, df)
        print(f"  k={k:2d}  blocks={nb:7d}  chi2={stat:9.1f}  df={df:5d}  p={p:.3f}")


def close_calls(dev, sel, N):
    m = np.arange(N + 1)
    print("\nclose calls.  Non-selected steps: distance below the threshold, scaled: (1/2 - u_m) 2^m  (stall needs this < 0)")
    ns = ~sel[:N]
    d = dev[:N]
    with np.errstate(divide="ignore"):
        score = np.log2(np.abs(d)) + m[:N]
    pos_ns = ns & (d > 0)
    print("   non-selected with u_m > 1/2:", int(pos_ns.sum()))
    idx = np.flatnonzero(ns)
    order = idx[np.argsort(score[idx])][:8]
    for i in order:
        print(f"   m={i:7d}  u_m={d[i]+0.5:.6f}  (1/2-u)2^m = {2.0**score[i]:.4f}")
    print("  selected steps closest above the threshold 1/2 + 2^-m-2: (u - 1/2) 2^m  (must be >= 1/4)")
    idx = np.flatnonzero(sel[:N])
    order = idx[np.argsort(score[idx])][:6]
    for i in order:
        print(f"   m={i:7d}  u_m={d[i]+0.5:.6f}  (u-1/2)2^m = {2.0**score[i]:.4f}")
    # tail-probability heuristic: #non-selected with (1/2-u)2^m < t  vs  t * sum 2^-m ~ t
    for t in [1, 2, 4, 8, 16]:
        n = int((ns & (score < np.log2(t))).sum())
        print(f"   #non-selected with (1/2-u)2^m < {t:2d}: {n}   (coin model expects about {t})")


def plots(A, dev, sel, N, out):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    gaps = np.diff(A)
    fig, axes = plt.subplots(3, 2, figsize=(14, 13))
    ax = axes[0, 0]
    ax.plot(A[1:300], gaps[:299], ".-", lw=0.6, ms=4)
    ax.set_title("gap to the previous element, first 300 elements of A (x = 1/2)")
    ax.set_xlabel("a"); ax.set_ylabel("gap")
    ax = axes[0, 1]
    cnt = Counter(gaps.tolist())
    gs = sorted(cnt)
    ax.semilogy(gs, [cnt[g] / len(gaps) for g in gs], "o", label="observed")
    ax.semilogy(gs, [2.0 ** -g for g in gs], "-", label="geometric 2^-g")
    ax.set_title("gap distribution vs fair coin"); ax.set_xlabel("gap"); ax.legend()
    ax = axes[1, 0]
    ind = np.zeros(N + 1); ind[A] = 1
    S = np.cumsum(ind[1:] - 0.5)
    n = np.arange(1, N + 1)
    ax.plot(n, S, lw=0.5, label="x=1/2")
    for seed in range(3):
        Ac = control(N, seed)
        ic = np.zeros(N + 1); ic[Ac] = 1
        ax.plot(n, np.cumsum(ic[1:] - 0.5), lw=0.4, alpha=0.5, label=f"coin {seed}")
    ax.plot(n, np.sqrt(n) / 2, "k--", lw=0.6); ax.plot(n, -np.sqrt(n) / 2, "k--", lw=0.6)
    ax.set_title("discrepancy S_n = #(A ∩ [1,n]) - n/2, with ±√n/2"); ax.legend(fontsize=8)
    ax = axes[1, 1]
    ax.hist(dev[:N] + 0.5, bins=50, range=(0, 1))
    ax.set_title("histogram of u_m = 2^m r_m (uniform under the coin model)")
    ax = axes[2, 0]
    mm = np.arange(1, 41)
    z = (dev[1:41]) * 2.0 ** mm
    cols = ["C3" if s else "C0" for s in sel[1:41]]
    ax.bar(mm, np.clip(z, -3, 3), color=cols)
    ax.axhspan(1 / 12, 1 / 4, color="red", alpha=0.2, label="stall window (1/12, 1/4)")
    ax.axhline(0.25, color="k", lw=0.5)
    ax.set_title("z_m = 2^m (u_m - 1/2), first 40 steps (red = m+1 selected), clipped to ±3")
    ax.set_xlabel("m"); ax.legend()
    ax = axes[2, 1]
    # density in windows
    w = 10000
    dens = ind[1:N - N % w + 1].reshape(-1, w).mean(axis=1)
    ax.plot(np.arange(len(dens)) * w, dens, ".-")
    ax.axhline(0.5, color="k", lw=0.5)
    ax.set_title(f"density of A in windows of {w}")
    fig.tight_layout(); fig.savefig(out, dpi=110)
    print("saved", out)


if __name__ == "__main__":
    path = sys.argv[1]
    A, c, dev, sel, flags, cnt = load(path)
    N = len(sel) - 1
    print("flags:", flags.tolist())
    gap_stats(A, path)
    ind = discrepancy(A, N)
    autocorr(ind, 24)
    residues(A, N)
    Dlt = parity_rule(A, c, cnt, sel, N)
    special_numbers(A, N, Dlt)
    block_test(A, N)
    close_calls(dev, sel, N)
    if "--plot" in sys.argv:
        plots(A, dev, sel, N, path.replace(".npz", ".png"))
