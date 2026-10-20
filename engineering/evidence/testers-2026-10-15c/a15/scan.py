def primerange(a,b):
    return [x for x in range(max(a,2),b) if all(x%d for d in range(2,int(x**.5)+1))]
bad=[]
for k in range(2,400,2):
    if k%3==0: continue
    ps=list(primerange(2,k+1))
    for n in range(2*k,k*k):
        if all(n%p>=k%p for p in ps): bad.append((n,k))
print(bad)
