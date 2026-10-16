#!/bin/zsh
cd ${0:a:h}
S=/private/tmp/claude-501/-Users-mikehiggins-Desktop-repos-open-proof-network/85614363-b225-4c5e-8f33-6eebe144b2d6/scratchpad/a01
N=erdos-1094--h2--h2--h2--h3--h1--h1--h1--h1
b() { python3 -c "import json,sys;d=json.load(open(sys.argv[1]));print(json.dumps(d.get('body',d)))" $1; }
until python3 -c "import json;d=json.load(open('tut-res.json'));b=d.get('body',d);exit(0 if b.get('state') in('done','error') else 1)" 2>/dev/null; do sleep 5; done
echo "$(date -u +%T) tutorial: $(b tut-res.json | head -c 300)"
python3 -c "
import json;print(json.dumps({'proof':{'kind':'tutorial','job_id':'01M500G97GS9W9VPBAEX6KAXT2','nonce':'VFX4Y1mjr4aXPxP60t85xzmNHQhYx6lJ'},'pseudonym':'t1015c-a01','dco':{'version':'1b72bc16f46ab19b','accepted':True}}))" > tok-args.json
for i in 1 2 3; do timeout 140 python3 mcp.py get_token "$(cat tok-args.json)" $S/tokresp.json && break; done
python3 -c "
import json;d=json.load(open('$S/tokresp.json'));b=d.get('body',d);t=b.get('token')
print('token?', bool(t), json.dumps(b.get('identity'))[:200] if t else json.dumps(d)[:400])
t and open('$S/token','w').write(t)"
[[ -f $S/token ]] || exit 1
for i in 1 2 3; do timeout 140 python3 mcp.py claim_node "{\"node_id\":\"$N\",\"ttl\":2}" claim.json && break; done
echo "$(date -u +%T) claim: $(b claim.json | head -c 400)"
for i in 1 2 3; do timeout 140 python3 mcp.py precheck_submission "$(cat pre-args.json)" pre.json && break; done
echo "$(date -u +%T) precheck: $(b pre.json | head -c 400)"
J=$(python3 -c "import json;d=json.load(open('pre.json'));b=d.get('body',d);print(b.get('id') or d.get('job_id'))")
echo "JOB $J"
./poll.sh $J pre-res.json
echo "$(date -u +%T) verdict: $(python3 -c "import json;d=json.load(open('pre-res.json'));b=d.get('body',d);r=b.get('result') or {};print(b.get('state'),r.get('verdict'),r.get('first_failing_step'))")"
