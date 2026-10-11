import sys
from math import gcd,lcm
from functools import reduce
import networkx as nx
for n in range(int(sys.argv[1]),int(sys.argv[2])+1):
    L=reduce(lcm,range(1,n)); V=sorted({L*j//k for k in range(2,n) for j in range(1,k)})
    G=nx.Graph(); G.add_nodes_from(V)
    for i,a in enumerate(V):
        for b in V[i+1:]:
            if n*gcd(a,b)>b: G.add_edge(a,b)
    best=min(max(nx.coloring.greedy_color(G,s).values())+1 for s in ('DSATUR','largest_first','smallest_last','independent_set'))
    print(n,len(V),'greedy colours',best,'target',n-2,'OK' if best<=n-2 else 'greedy-short',flush=True)
