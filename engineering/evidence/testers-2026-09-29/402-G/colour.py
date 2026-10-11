import math, sys, itertools
from fractions import Fraction
def setup(n):
    L = math.lcm(*range(1, n))
    vals = sorted({L*j//k for k in range(2, n) for j in range(1, k)})
    return L, vals
def good(n,a,b): g=math.gcd(a,b); return n*g<=a or n*g<=b
def colour(n, ncol):
    L, vals = setup(n)
    bad = {v:set() for v in vals}
    for a,b in itertools.combinations(vals,2):
        if not good(n,a,b): bad[a].add(b); bad[b].add(a)
    # DSATUR-ish backtracking
    order = sorted(vals, key=lambda v:-len(bad[v]))
    col = {}
    def bt(i):
        if i==len(order): return True
        v=order[i]
        used={col[u] for u in bad[v] if u in col}
        for c in range(ncol):
            if c not in used:
                col[v]=c
                if bt(i+1): return True
                del col[v]
        return False
    ok = bt(0)
    return L, vals, col if ok else None
if __name__=='__main__':
    for n in map(int, sys.argv[1:]):
        L, vals, col = colour(n, n-2)
        print(n, 'L', L, 'values', len(vals), 'colouring into', n-2, 'found' if col else 'NONE')
        if col:
            # verify
            for a,b in itertools.combinations(vals,2):
                if col[a]==col[b]: assert good(n,a,b)
            # also sanity: every x = j/k M form
            print(' classes:', [sorted(v for v in vals if col[v]==c) for c in range(n-2)])
