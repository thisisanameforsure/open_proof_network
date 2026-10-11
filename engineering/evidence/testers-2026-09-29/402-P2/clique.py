import sys, networkx as nx
from math import gcd, lcm
from functools import reduce
for n in map(int, sys.argv[1:]):
    L=reduce(lcm,range(1,n),1)
    S=sorted({L//k*j for k in range(1,n) for j in range(1,k)})
    G=nx.Graph(); G.add_nodes_from(S)
    for i,v in enumerate(S):
        for w in S[i+1:]:
            if n*gcd(v,w) > max(v,w): G.add_edge(v,w)
    c,_=nx.max_weight_clique(G, weight=None)
    print(n, len(S), "maxclique", len(c), "need colours", n-2, flush=True)
