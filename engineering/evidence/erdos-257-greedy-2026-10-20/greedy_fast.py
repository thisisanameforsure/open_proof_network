"""Fast greedy walk for x = sum_{a in A} 1/(2^a - 1), with exact integer carries.

State after deciding positions 1..m:
  r_m   = x - sum_{a in A, a<=m} 1/(2^a-1)          (remainder)
  u_m   = 2^m r_m                                   (scaled remainder, in [0, 1+2^-m/3])
  c_m   = integer carry  = 2^m x - sum_{a in A} sum_{k: ka<=m} 2^(m-ka)   (exact int)
  f_m   = sum_{j>=1} cnt_m[m+j] 2^-j   where cnt_m[t] = #{a in A, a<=m : a | t}
  u_m   = c_m - f_m                                 (exact identity)
Decision: m+1 in A  iff  u_m >= 2^m/(2^(m+1)-1).
f_m is held in fixed point with J fractional bits (truncated, so F <= true F <= F + maxcnt);
a decision is only taken when both bounds agree, otherwise the step is flagged.
"""
from __future__ import annotations

import sys
from fractions import Fraction

import numpy as np


def run(p: int, q: int, N: int, J: int = 256):
    assert q & (q - 1) == 0, "q must be a power of two"
    k = q.bit_length() - 1
    size = N + J + 2
    cnt = np.zeros(size, dtype=np.int64)
    A: list[int] = []
    # exact emulation of the first k steps (x = p/2^k is not yet an integer multiple of 2^-m)
    r = Fraction(p, q)
    m = 0
    while m < k:
        t = Fraction(1, 2 ** (m + 1) - 1)
        if r >= t:
            r -= t
            A.append(m + 1)
            cnt[m + 1 :: m + 1] += 1
        m += 1
    fr = sum((Fraction(2 ** (m % a), 2 ** a - 1) for a in A), Fraction(0))
    c = int(r * 2**m + fr)
    assert Fraction(c) - fr == r * 2**m
    F = sum(int(cnt[m + j]) << (J - j) for j in range(1, J + 1))
    maxcnt = 4096
    stuck = 0
    two_J = 1 << J
    half = 1 << (J - 1)
    dev = np.zeros(N + 1)            # u_m - 1/2 as float (exact integer difference, then rounded)
    sel_arr = np.zeros(N + 1, dtype=bool)
    cseq = np.zeros(N + 1, dtype=np.int64)
    flags = []
    while m < N:
        U = (c << J) - F
        if m >= J:
            T = half + 1  # ceil(2^(m+J)/(2^(m+1)-1)) once 2^(J-1-m) < 1/2
        else:
            den = (1 << (m + 1)) - 1
            T = ((1 << (m + J)) + den - 1) // den
        hi = U >= T
        lo = U - maxcnt >= T
        if hi != lo:
            flags.append(m)
        sel = hi
        d = U - half
        dev[m] = d / two_J if abs(d) < (1 << 1000) else float(d) / two_J
        sel_arr[m] = sel
        a = m + 1
        cnt_far = int(cnt[a + J])
        add = 0
        if sel:
            A.append(a)
            cnt[a::a] += 1
            kk = a
            while kk <= J:
                add += 1 << (J - kk)
                kk += a
        D = int(cnt[a])
        c = 2 * c - D
        F = 2 * F - (D - (1 if sel else 0)) * two_J + cnt_far + add
        m += 1
        cseq[a] = c
        # stall test: u_m > 2^m tail_m = 1 + delta_m, delta_m < 2^-m. U_true in [U - maxcnt, U].
        U = (c << J) - F
        bound = two_J + (1 << max(J - m, 0))  # certain stall if U_true > this
        if U - maxcnt > bound:
            print("STUCK at m =", m, "c =", c, "u-1 =", (U - two_J) / two_J, file=sys.stderr)
            stuck = m
            break
        if U > two_J:
            print("near/possible stall at m =", m, "U-2^J =", U - two_J, file=sys.stderr)
            flags.append(-m)
    assert cnt.max() <= maxcnt, cnt.max()
    return A, cseq, dev, sel_arr, flags, cnt, stuck


if __name__ == "__main__":
    p, q, N = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3])
    out = sys.argv[4]
    A, cseq, dev, sel_arr, flags, cnt, stuck = run(p, q, N)
    np.savez_compressed(out, A=np.array(A), c=cseq, dev=dev, sel=sel_arr,
                        flags=np.array(flags), cnt=cnt[: N + 1], stuck=stuck)
    print(f"x={p}/{q} N={N} |A|={len(A)} flags={flags[:10]} maxc={cseq.max()} stuck={stuck} maxcnt={cnt.max()}")
