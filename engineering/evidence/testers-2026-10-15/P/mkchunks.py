import json
D=json.load(open('decls.json'))
H="import Mathlib\nnoncomputable section\nopen scoped BigOperators Nat MatrixOrder\nopen Finset Filter\n\n"
chunks=[];cur=[];size=0
for i,d in enumerate(D):
    cur.append(i); size+=len(d['full'])
    if size>(6500 if i<60 else 13000): chunks.append(cur);cur=[];size=0
if cur: chunks.append(cur)
for c,idx in enumerate(chunks):
    pre='\n'.join(D[j]['stub'] for j in range(idx[0]))
    body='\n'.join(D[j]['full'] for j in idx)
    open(f'chunks/c{c:02d}.lean','w').write(H+pre+'\n\n'+body+'\n')
    print(c, D[idx[0]]['name'], '..', D[idx[-1]]['name'], len(H+pre+body))
