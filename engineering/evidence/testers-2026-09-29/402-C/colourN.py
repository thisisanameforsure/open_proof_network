from math import gcd, lcm
import sys, itertools, signal
def run(N, budget=20):
    L=1
    for k in range(1,N): L=lcm(L,k)
    S=sorted({L//k*j for k in range(2,N) for j in range(1,k)})
    conflict=lambda a,b: N*gcd(a,b) > max(a,b)
    adj={a:{b for b in S if b!=a and conflict(a,b)} for a in S}
    K=N-2; col={}
    def pick():
        best=None;bk=None
        for a in S:
            if a in col: continue
            key=(len({col[b] for b in adj[a] if b in col}),len(adj[a]))
            if bk is None or key>bk: bk=key;best=a
        return best
    def rec():
        if len(col)==len(S): return True
        a=pick(); used={col[b] for b in adj[a] if b in col}
        for c in range(K):
            if c not in used:
                col[a]=c
                if rec(): return True
                del col[a]
        return False
    signal.alarm(budget)
    try: ok=rec()
    except TimeoutError: ok=None
    signal.alarm(0)
    return L,len(S),K,ok
def h(*a): raise TimeoutError
signal.signal(signal.SIGALRM,h)
for N in range(9,21):
    print(N, run(N), flush=True)
