import sys
st = open('h3h1_Statement.lean').read()
body = open('skel_body.lean').read()
annex = sys.argv[1] if len(sys.argv) > 1 else None
cite = f"  -- annex: {annex}\n" if annex else ""
out = st.replace(":= by\n  sorry\n", ":= by\n" + cite + body)
assert out != st
open('skeleton.lean', 'w').write(out)
print(out)
