exec(open('head-integral-by-difference.py').read().split('for n in range(1,19):')[0])
# Which parts of the multiplier 9^n P(n) L_{n-1} does T = sum_k k A(n,k) need?  Compare with beta0 = sum_k A(n,k).
for n in range(1,31):
    As={k:A(n,k) for k in range(1,n+1)}
    L=1
    for d in range(1,n): L*=Phi(d)
    T=sum(k*As[k] for k in range(1,n+1)); b0=sum(As.values())
    print(n,'den(T)',fac(T.denominator),'| den(L_{n-1} T)',fac((L*T).denominator),'| den(beta0)',fac(b0.denominator),flush=True)
