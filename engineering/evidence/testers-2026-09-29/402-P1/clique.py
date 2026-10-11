# For card n: values c = L*j/k (1<=j<k<=n-1, L=lcm(1..n-1)); bad pair iff n*gcd(c,d) > max(c,d).
# The max-element route works for card n iff the bad graph has no clique of size n-1 (n-1 distinct values pairwise bad).
import sys,time
from math import gcd,lcm
from functools import reduce
import networkx as nx
for n in range(int(sys.argv[1]),int(sys.argv[2])+1):
    t=time.time()
    L=reduce(lcm,range(1,n))
    V=sorted({L*j//k for k in range(2,n) for j in range(1,k)})
    G=nx.Graph(); G.add_nodes_from(V)
    for i,a in enumerate(V):
        for b in V[i+1:]:
            if n*gcd(a,b)>b: G.add_edge(a,b)
    cl,w=nx.max_weight_clique(G,weight=None)
    print(n,len(V),G.number_of_edges(),'omega',w,'need<=',n-2,'OK' if w<=n-2 else 'FAILS', 'clique(as j/k)',[f"{c//gcd(c,L)}/{L//gcd(c,L)}" for c in sorted(cl)], f"{time.time()-t:.1f}s",flush=True)
