import sys; sys.argv=['x']
exec(open('audit.py').read().split("def mpf")[0])
bad=[]
for n in range(1, 41):
    b0,a0,N=exact(n)
    b,a=N*b0,N*a0
    ok = b.denominator==1 and a.denominator==1
    # also: without the (n-2)! factor, and without the 9^n factor
    from math import factorial
    fct=F(factorial(max(n-2,0)))
    ok_nofact = (b/fct).denominator==1 and (a/fct).denominator==1
    print(n, "integral" if ok else f"NOT integral (den b {b.denominator}, a {a.denominator})", "| without (n-2)!:", "integral" if ok_nofact else "not", "| digits of b:", len(str(abs(b.numerator))))
    if not ok: bad.append(n)
print("non-integral n:", bad)
