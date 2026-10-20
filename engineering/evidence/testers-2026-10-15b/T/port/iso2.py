import re,sys,os
# iso2.py <file> <outprefix>: one variant per `have ... := by` block (single-line header), keeping only that block + ancestors + descendants proved
L=open(sys.argv[1]).read().split('\n')
ind=lambda s: len(s)-len(s.lstrip(' '))
blocks=[]
for i,l in enumerate(L):
    if re.match(r'^\s+have .*:= by\s*$',l) or re.match(r'^\s+have .*:= by$',l):
        n=ind(l); j=i+1
        while j<len(L) and (L[j].strip()=='' or ind(L[j])>n): j+=1
        blocks.append((i,j,n))
for k,(a,b,n) in enumerate(blocks):
    keep=set()
    out=[];i=0
    others=[(x,y,m) for (x,y,m) in blocks if not (x<=a and y>=b) and not (x>=a and y<=b)]
    # outermost of others
    outer=[o for o in others if not any(p!=o and p[0]<=o[0] and p[1]>=o[1] for p in others)]
    skip={}
    for (x,y,m) in outer: skip[x]=y
    while i<len(L):
        if i in skip:
            out.append(L[i].rstrip()[:-len(':= by')]+':= by sorry'); i=skip[i]
        else:
            out.append(L[i]); i+=1
    open(f"{sys.argv[2]}.{k}.lean",'w').write('\n'.join(out))
    print(k,a,n,L[a].strip()[:80])
