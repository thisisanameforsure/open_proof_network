import sys
sys.setrecursionlimit(100000)
exec(open('col2.py').read().split('for N in')[0])
for N in range(19,31):
    L,n,K,ok,col=run(N, limit=3_000_000)
    print(N,'values',n,'colours',K,'ok',ok, flush=True)
