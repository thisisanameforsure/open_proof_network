import json,base64,struct,hashlib,sys
import nacl.signing
def S(x): return struct.pack(">I",len(x))+x
def rd(b,i):
    n=struct.unpack(">I",b[i:i+4])[0]; return b[i+4:i+4+n], i+4+n
def parse(sig):
    b=base64.b64decode("".join(l for l in sig.splitlines() if not l.startswith("-----")))
    assert b[:6]==b"SSHSIG"; i=10
    pk,i=rd(b,i); ns,i=rd(b,i); res,i=rd(b,i); ha,i=rd(b,i); s,i=rd(b,i)
    kt,j=rd(pk,0); key,j=rd(pk,j); st,j=rd(s,0); raw,j=rd(s,j)
    return pk,ns,res,ha,key,raw
def cands(a):
    body=dict(a); sigobj=body.pop("signature")
    out={}
    for name,doc in [("no-signature",body),("sig-without-value",dict(body,signature={k:v for k,v in sigobj.items() if k!="value"})),("sig-null",dict(body,signature=None)),("sig-value-null",dict(body,signature=dict(sigobj,value=None))),("sig-value-empty",dict(body,signature=dict(sigobj,value="")))]:
        for sk in (True,False):
            for sep in [(",",":"),(", ",": "),None]:
                for ea in (True,False):
                    for ind in (None,1,2):
                        m=json.dumps(doc,sort_keys=sk,separators=sep,ensure_ascii=ea,indent=ind).encode()
                        k=f"{name} sort={sk} sep={sep} ascii={ea} indent={ind}"
                        out[k]=m; out[k+" +nl"]=m+b"\n"
    return out
def verify(a, pubfile):
    pk,ns,res,ha,key,raw=parse(a["signature"]["value"])
    kf=base64.b64decode(open(pubfile).read().split()[1])
    vk=nacl.signing.VerifyKey(key)
    ok=[]
    for k,m in cands(a).items():
        h=hashlib.sha512(m).digest() if ha==b"sha512" else hashlib.sha256(m).digest()
        blob=b"SSHSIG"+S(ns)+S(res)+S(ha)+S(h)
        try: vk.verify(blob,raw); ok.append(k)
        except Exception: pass
    return ns, ha, kf==pk, ok
if __name__=="__main__":
    a=json.load(open(sys.argv[1])); a=a.get("result",{}).get("attestation",a) if "result" in a else a
    ns,ha,keyok,ok=verify(a, sys.argv[2])
    print("namespace",ns,"hash",ha,"key matches",keyok,"verified by:",ok[:4], len(ok))
