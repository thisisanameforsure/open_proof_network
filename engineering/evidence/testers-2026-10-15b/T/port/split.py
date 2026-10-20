import re,json,sys
s=open('../vdt/ErdosProblem451.lean').read()
lines=s.split('\n')
seg='\n'.join(lines[133:2430])
t=re.sub(r'/-.*?-/','',seg,flags=re.S)
t=re.sub(r'(?m)^\s*--[^\n]*\n','',t)
t=re.sub(r'[ ]+\n','\n',t)
t=re.sub(r'\n\s*\n+','\n',t)
L=t.split('\n')
decls=[];cur=None
for ln in L:
    if re.match(r'^(lemma|theorem|def) ',ln):
        cur={'kind':ln.split()[0],'name':ln.split()[1],'text':[ln]}; decls.append(cur)
    elif re.match(r'^(set_option|open|end|noncomputable section)',ln):
        cur=None
    else:
        if cur is None:
            if ln.strip(): print('ORPHAN',ln[:80],file=sys.stderr)
            continue
        cur['text'].append(ln)
def stub(d):
    txt='\n'.join(d['text'])
    if d['kind']=='def': return txt
    depth=0;i=len(d['kind'])
    while i<len(txt)-1:
        c=txt[i]
        if c in '([{⟨': depth+=1
        elif c in ')]}⟩': depth-=1
        elif c==':' and txt[i+1]=='=' and depth==0:
            ls=txt.rfind('\n',0,i)+1
            if not re.match(r'\s*let ',txt[ls:i]) and ' let ' not in txt[ls:i]:
                return txt[:i]+':= by sorry'
        i+=1
    raise Exception('no := in '+d['name'])
for d in decls: d['full']='\n'.join(d['text']); d['stub']=stub(d)
json.dump([{k:d[k] for k in('kind','name','full','stub')} for d in decls],open('decls.json','w'),ensure_ascii=False)
for i,d in enumerate(decls): print(i,d['kind'],d['name'],len(d['full']))
