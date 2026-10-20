import sys
KMAX=int(sys.argv[1])
pr=[p for p in range(2,KMAX+1) if all(p%q for q in range(2,int(p**.5)+1))]
def good(n,k):
    for p in pr:
        if p>k: return False
        if n%p < k%p: return True
    return False
last={'A_even_k3':0,'B_even_rest':0,'A_odd_k3':0,'B_odd_rest':0}; cnt={x:0 for x in last}
for k in range(3,KMAX+1):
    for n in range(2*k,k*k):
        if k%2==0: lab='A_even_k3' if k%3==0 else ('B_even_rest' if k%3<=n%3 else None)
        elif n%2==1: lab='A_odd_k3' if k%3==0 else ('B_odd_rest' if k%3<=n%3 else None)
        else: continue
        if lab is None:
            assert good(n,k)  # p=3 case must work
            continue
        if not good(n,k): last[lab]=max(last[lab],k); cnt[lab]+=1
print(KMAX, last, cnt)
