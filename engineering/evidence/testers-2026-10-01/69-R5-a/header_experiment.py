import json,urllib.request,sys
def chk(extra_import, tag):
    c = "import Defs.IsPrime\n" + extra_import + "import Mathlib.Tactic\nimport Nodes.«infinitude-of-primes».Context\n\ntheorem Opn.infinitude_of_primes : ∀ n : Nat, ∃ p : Nat, n < p ∧ Opn.IsPrime p := by\n  have h : ∀ n : Nat, 0 < Opn.fact n := sorry\n  sorry\n"
    req=urllib.request.Request('https://api.openproofnetwork.org/check',data=json.dumps({"target_id":"euclid-primes","mode":"verify","node_id":"infinitude-of-primes","content":c}).encode(),headers={'Content-Type':'application/json'})
    try: r=json.load(urllib.request.urlopen(req,timeout=120))
    except urllib.error.HTTPError as e: print(tag,e.code,e.read()[:1500]); return
    res=r.pop('result',{}) or {}
    print(tag, json.dumps(r)[:1500]); print(json.dumps(res)[:1500])
chk("import Defs.Fact\n","WITH Defs.Fact:")
chk("","WITHOUT:")
