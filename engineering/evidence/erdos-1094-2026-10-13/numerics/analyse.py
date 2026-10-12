"""Per-node figures for erdos-1094 from the complete searches (k <= 1000).
good3.out: every (n,k) with 2k <= n < k^3 and no prime p <= k dividing C(n,k)  ("good").
resid.out: every (n,k) with 2k <= n < k^2 and no prime p <= k with n % p < k % p."""
import math
def lpf(m):
    p = 2
    while p * p <= m:
        if m % p == 0: return p
        p += 1
    return m
good = [tuple(map(int, l.split()[1:])) for l in open('good3.out')]
res = [tuple(map(int, l.split()[1:])) for l in open('resid.out')]
# root exceptions with n < k^3: good pairs where also lpf > n//k
root = sorted([(n, k) for n, k in good if lpf(math.comb(n, k)) > max(n // k, k)], key=lambda t: (t[1], t[0]))
print('root exceptions, n < k^3, k <= 1000:', len(root), root)
ELS = {(7,3),(13,4),(14,4),(23,5),(44,8),(46,10),(47,10),(47,11),(62,6),(74,10),(94,10),(95,10),(241,16),(284,28)}
print('equals ELS 14:', set(root) == ELS)
def node(name, pairs):
    ks = [k for _, k in pairs]
    print(f'{name}: {len(pairs)} pairs; largest k = {max(ks) if ks else None}; last pairs {sorted(pairs, key=lambda t:(t[1],t[0]))[-3:]}')
h3 = [(n,k) for n,k in good if n < k*k]                       # lpf > k, 2k<=n<k^2
h2h1h1 = good                                                   # lpf > k, 2k<=n<k^3
h2h1 = [(n,k) for n,k in good if k*k <= n and lpf(math.comb(n,k)) > n//k]
node('h3 (2k<=n<k^2, lpf>k)', h3)
node('h2--h1--h1 (2k<=n<k^3, lpf>k)', h2h1h1)
node('h2--h1 (k^2<=n<k^3, lpf>n/k)', h2h1)
node('h3--h1 (residue form)', res)
node('h3--h1--h1 (k even)', [(n,k) for n,k in res if k % 2 == 0])
node('h3--h1--h2 (k odd, n odd)', [(n,k) for n,k in res if k % 2 == 1 and n % 2 == 1])
print('residue failures with k odd and n even:', [(n,k) for n,k in res if k % 2 == 1 and n % 2 == 0])
print('good pairs (h3 range) all among residue failures:', set(h3) <= set(res))
