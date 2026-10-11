import json,sys,urllib.request,time
def check(content,target='erdos-69',node=None,mode='check'):
    body={"target_id":target,"mode":mode,"content":content}
    if node: body["node_id"]=node
    req=urllib.request.Request('https://api.openproofnetwork.org/check',data=json.dumps(body).encode(),headers={'Content-Type':'application/json'})
    t=time.time()
    try:
        r=json.load(urllib.request.urlopen(req,timeout=120))
    except urllib.error.HTTPError as e:
        return {'http':e.code,'body':e.read()[:600].decode(),'secs':time.time()-t}
    r['secs']=time.time()-t
    return r
def summ(r):
    if 'http' in r: return r
    res=r.get('result') or {}
    errs=(res.get('lean_messages') or {}).get('errors') or res.get('errors') or []
    return {'okay':r.get('okay'),'env':r.get('environment'),'exact':r.get('exact'),'secs':round(r['secs'],1),'lint':[w.get('code') for w in r.get('lint',[])],'nerr':len(errs),'errs':[str(e)[:400] for e in errs[:6]],'user_error':r.get('user_error')}
if __name__=='__main__':
    print(json.dumps(summ(check(open(sys.argv[1]).read(),node=(sys.argv[2] if len(sys.argv)>2 else None))),indent=1,ensure_ascii=False))
