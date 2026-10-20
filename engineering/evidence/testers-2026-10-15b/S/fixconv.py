import re,sys
p=sys.argv[1]; t=open(p).read()
new=' <;> (try (first | with_reducible_and_instances rfl | (show (_ : LE ℝ) = _; rfl) | (show (_ : LT ℝ) = _; rfl) | (show (_ : LE ℝ) = _; with_unfolding_all rfl) | (show (_ : LT ℝ) = _; with_unfolding_all rfl)))'
out=[];pos=0;n=0
for m in re.finditer(r'\bconvert\b',t):
    if m.start()<pos: continue
    i=m.end();depth=0
    while i<len(t):
        ch=t[i]
        if ch in '([{⟨': depth+=1
        elif ch in ')]}⟩':
            depth-=1
            if depth<0: break
        if depth==0:
            mm=re.match(r' using \d+',t[i:])
            if mm:
                end=i+mm.end()
                if not t[end:].startswith(' <;> (try (first'):
                    out.append(t[pos:end]+new); pos=end; n+=1
                break
            if t[i]=='\n' and re.match(r'\n\s*(·|have|exact|rw|refine|apply|simp|norm_num|linarith|nlinarith|obtain|intro|by_cases|calc|--)',t[i:]) : break
        i+=1
out.append(t[pos:]); open(p,'w').write(''.join(out)); print('inserted',n)
