from sympy import primerange
last=0; cnt=0; cov=0; tot=0
for k in range(8,301,2):
    if k%3==0: continue
    ps=list(primerange(2,k+1))
    for n in range(2*k,k*k):
        if not (k%3<=n%3): continue
        tot+=1
        if all(k%q<=n%q for q in (5,7,11,13)):
            cov+=1
            if not any(n%p<k%p for p in ps): last=k; cnt+=1
print("parent cases",tot,"left to hole",cov,"failures in hole",cnt,"last failing k",last)
