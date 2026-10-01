# 402-R6-b: honest width of the generalised window. For size n the criterion needs every α in (p-n, n) to be "good"
# (no x<y, x*y | α, α*y < n*x) unless a prime q >= n/3 divides α(p-α). Ignoring the q-escape, the window ends at the
# first bad α below n: s1(n) = n - max{bad α < n}; then p must satisfy p - n >= α_bad, i.e. 2n - p <= s1(n).
import math, random
def divisors(a):
    d=[]; i=1
    while i*i<=a:
        if a%i==0:
            d.append(i)
            if i*i!=a: d.append(a//i)
        i+=1
    return sorted(d)
def bad(al,n):
    D=divisors(al)
    for x in D:
        if x*x>al: break
        for y in D:
            if y>x and al%(x*y)==0 and al*y<n*x: return True
    return False
def s1(n):
    s=1
    while not bad(n-s,n): s+=1
    return s
random.seed(1)
for lo,hi,cnt in [(10**3,2*10**3,400),(10**4,2*10**4,400),(10**5,2*10**5,400),(10**6,2*10**6,300),(10**7,2*10**7,200),(10**8,2*10**8,100)]:
    r=[]
    for _ in range(cnt):
        n=random.randrange(lo,hi); r.append(s1(n)/math.sqrt(n))
    r.sort()
    print("n in [%d,%d): first bad α at distance s1; s1/sqrt(n): min %.2f median %.2f max %.2f"%(lo,hi,r[0],r[len(r)//2],r[-1]))
