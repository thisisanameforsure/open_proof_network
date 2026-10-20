"""Statistics of a greedy walk saved by greedy_fast.py, against a random-coin control."""
from __future__ import annotations

import sys
from collections import Counter

import numpy as np


def load(path):
    d = np.load(path)
    return d["A"], d["c"], d["dev"], d["sel"], d["flags"], d["cnt"]


def gap_stats(A, label):
    gaps = np.diff(A)
    N = A[-1]
    print(f"\n== {label}: |A|={len(A)} through {N}, density {len(A)/N:.5f}")
    print("first 60 elements:", A[:60].tolist())
    print("first 60 gaps:    ", gaps[:60].tolist())
    cnt = Counter(gaps.tolist())
    total = len(gaps)
    print("gap  count   observed  geometric(1/2)  ratio")
    for g in sorted(cnt):
        if cnt[g] >= 5 or g <= 12:
            exp = total * 2.0 ** (-g)
            print(f"{g:3d} {cnt[g]:7d}  {cnt[g]/total:9.5f}  {2.0**(-g):9.5f}   {cnt[g]/exp:6.3f}")
    print("max gap:", gaps.max(), "at a =", A[np.argmax(gaps)], "; log2(N) =", np.log2(N))
    print("mean gap:", gaps.mean(), "(geometric: 2)")
    # runs of consecutive elements
    runs = []
    r = 1
    for g in gaps:
        if g == 1:
            r += 1
        else:
            runs.append(r)
            r = 1
    runs.append(r)
    rc = Counter(runs)
    print("run lengths (consecutive elements): ", {k: rc[k] for k in sorted(rc)[:12]}, "max", max(runs))
    return gaps


def discrepancy(A, N):
    ind = np.zeros(N + 1, dtype=np.int8)
    ind[A] = 1
    s = np.cumsum(ind[1:] - 0.5)
    print("discrepancy  sum(1_A - 1/2) up to n: max |S_n| =", np.abs(s).max(), " at n =", np.argmax(np.abs(s)) + 1,
          "; S_N =", s[-1], "; sqrt(N)/2 =", np.sqrt(N) / 2)
    checkpoints = [10**k for k in range(1, 7) if 10**k <= N]
    print("S_n at powers of ten:", [(n, int(s[n - 1])) for n in checkpoints])
    return ind


def autocorr(ind, lags=40):
    x = ind[1:].astype(float) - ind[1:].mean()
    n = len(x)
    v = (x * x).sum()
    out = []
    for k in range(1, lags + 1):
        out.append((x[:-k] * x[k:]).sum() / v)
    out = np.array(out)
    print(f"autocorrelation lags 1..{lags} (noise level ~ {1/np.sqrt(n):.5f}):")
    print(np.array2string(out, precision=4, max_line_width=120))
    big = [(k + 1, round(float(o), 4)) for k, o in enumerate(out) if abs(o) > 4 / np.sqrt(n)]
    print(" lags beyond 4 sigma:", big)


def residues(A, N):
    print("A modulo q (fraction of A in each class; a uniform random set gives 1/q each):")
    for q in [2, 3, 4, 5, 6, 7, 8]:
        c = np.bincount(A % q, minlength=q) / len(A)
        print(f"  q={q}: {np.array2string(c, precision=4)}")


def divisibility(A, N):
    ind = np.zeros(N + 1, dtype=bool)
    ind[A] = True
    # pairs (a, 2a), (a, 3a): P(2a in A | a in A) vs density
    for k in [2, 3, 4, 5, 6, 7]:
        a = A[A * k <= N]
        p = ind[a * k].mean()
        print(f"  P(k*a in A | a in A), k={k}: {p:.4f}   (n={len(a)})")
    # D(m) = number of a in A dividing m, for m in A vs m not in A
    cntA = np.zeros(N + 1, dtype=np.int32)
    for a in A:
        cntA[a::a] += 1
    inA = cntA[A]
    notA = cntA[1:][~ind[1:]]
    print(f"  mean #divisors-in-A: elements of A {inA.mean():.4f} (incl. itself), non-elements {notA.mean():.4f}")
    return cntA


def carries(c, cnt, sel, N):
    cc = Counter(c[1:N + 1].tolist())
    print("carry c_m distribution:", {k: cc[k] for k in sorted(cc)})
    dc = Counter(cnt[1:N + 1].tolist())
    print("D(m) = #{a in A : a | m} distribution:", {k: dc[k] for k in sorted(dc)})
    # relation between carry and selection
    for cv in sorted(cc):
        mask = c[1:N + 1] == cv
        # selection of m+1 is sel[m]; c index m -> c[m]
        s = sel[1:N + 1][mask].mean() if mask.any() else float("nan")
        print(f"  c_m={cv}: P(m+1 in A) = {s:.4f}  (n={mask.sum()})")


def near_stall(dev, sel, N):
    m = np.arange(N + 1)
    # non-selected steps: margin below threshold. threshold ~ 1/2 + 2^-m-2; stall window z in (1/12, 1/4)
    ns = ~sel[:N]
    d_ns = dev[:N][ns]
    m_ns = m[:N][ns]
    # z = 2^m (u - 1/2); log2 of |z| for the closest ones
    with np.errstate(divide="ignore"):
        z = np.where(d_ns == 0, -np.inf, np.log2(np.abs(d_ns))) + m_ns
    # for non-selected steps dev < 0 typically (u < 1/2); closest to stall = largest dev*2^m (i.e. least negative)
    order = np.argsort(-np.where(d_ns > 0, 1e9, 0) - z)  # positive dev first, then largest z
    print("non-selected steps closest to the stall window (z = 2^m (u_m - 1/2); stall iff z in (1/12, 1/4)):")
    pos = d_ns > 0
    print("   steps with u_m > 1/2 but not selected:", int(pos.sum()), "(expected a few in the early steps only)")
    for i in order[:8]:
        print(f"   m={m_ns[i]:7d}  u-1/2={d_ns[i]: .3e}  z={np.sign(d_ns[i])*2.0**z[i]: .4e}")
    # selected steps: how close above the threshold u >= 1/2 + 2^-m-2 ... z >= 1/4
    s = sel[:N]
    d_s = dev[:N][s]
    m_s = m[:N][s]
    with np.errstate(divide="ignore"):
        zs = np.log2(np.abs(d_s)) + m_s
    order = np.argsort(zs)
    print("selected steps closest to the threshold (z >= 1/4):")
    for i in order[:5]:
        print(f"   m={m_s[i]:7d}  u-1/2={d_s[i]: .3e}  z={2.0**zs[i]: .4e}")
    # heuristic: expected number of non-selected steps with z > -t is ~ t * sum 2^-m
    u = dev[:N] + 0.5
    h, _ = np.histogram(u, bins=10, range=(0, 1))
    print("histogram of u_m on [0,1] in tenths:", h.tolist())


def control(N, seed=0):
    rng = np.random.default_rng(seed)
    bits = rng.integers(0, 2, size=N + 1)
    bits[0] = 0
    return np.flatnonzero(bits)


if __name__ == "__main__":
    path = sys.argv[1]
    A, c, dev, sel, flags, cnt = load(path)
    N = len(sel) - 1
    print("flags (ambiguous decisions):", flags.tolist())
    gaps = gap_stats(A, path)
    ind = discrepancy(A, N)
    autocorr(ind)
    residues(A, N)
    divisibility(A, N)
    carries(c, cnt, sel, N)
    near_stall(dev, sel, N)
    if "--control" in sys.argv:
        Ac = control(N)
        gap_stats(Ac, "random coin control")
        discrepancy(Ac, N)
