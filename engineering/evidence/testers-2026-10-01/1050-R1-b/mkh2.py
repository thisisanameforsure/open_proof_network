import json
pc=json.load(open('pieces.json'))
h=open('h2-close.lean').read().rstrip('\n').split('\n')
inum=[j for j,l in enumerate(h) if l.startswith('  have numerator_integral')][0]
ikey=[j for j,l in enumerate(h) if l.startswith('    have key')][0]
iw3=[j for j,l in enumerate(h) if l.startswith('    have hW3')][0]
assert h[inum].endswith(':= erdos_1050__h1_v2__h2__h1') and h[ikey].endswith(':= by')
c="(8 / 3 : ℝ)"
Dk="∏ l ∈ (Finset.Icc 1 n).erase k, (1 - (2 : ℝ) ^ ((l : ℤ) - (k : ℤ)))"
newkey=f"""      intro n hn
      obtain ⟨α, hα⟩ := hpoly n hn
      have hA : ∀ k : ℕ, ∏ t ∈ Finset.Icc 1 (n - 1), (1 - {c} * (2 : ℝ) ^ (t + k)) = ∑ j ∈ Finset.range n, (α j : ℝ) * ({c} * 2 ^ k) ^ j := by
        intro k
        rw [← hα]
        refine Finset.prod_congr rfl (fun t _ => ?_)
        rw [pow_add]; ring
      simp only [hA]
      have e1 : ∑ k ∈ Finset.Icc 1 n, (-(∑ j ∈ Finset.range n, (α j : ℝ) * ({c} * 2 ^ k) ^ j) / {Dk}) = ∑ j ∈ Finset.range n, ∑ k ∈ Finset.Icc 1 n, (-(α j : ℝ)) * (({c} * (2 : ℝ) ^ k) ^ j / {Dk}) := by
        rw [Finset.sum_comm]
        refine Finset.sum_congr rfl (fun k _ => ?_)
        rw [neg_div, Finset.sum_div, ← Finset.sum_neg_distrib]
        refine Finset.sum_congr rfl (fun j _ => ?_)
        ring
      rw [e1, Finset.mul_sum]
      refine hsumZ _ _ (fun j hj => ?_)
      have hj' := Finset.mem_range.mp hj
      rw [← Finset.mul_sum]
      obtain ⟨w, hw⟩ := hW _ (Finset.Icc 1 n) j rfl
      refine ⟨-(α j) * 3 ^ (n - 1 - j) * 8 ^ j * w, ?_⟩
      have hpos : ∑ k ∈ Finset.Icc 1 n, ({c} * (2 : ℝ) ^ k) ^ j / {Dk} = {c} ^ j * ∑ k ∈ Finset.Icc 1 n, ((2 : ℝ) ^ k) ^ j / {Dk} := by
        rw [Finset.mul_sum]
        refine Finset.sum_congr rfl (fun k _ => ?_)
        rw [mul_pow, mul_div_assoc]
      have h3 : (3 : ℝ) ^ (n - 1) = 3 ^ (n - 1 - j) * 3 ^ j := by rw [← pow_add]; congr 1; omega
      have h83 : {c} ^ j * 3 ^ j = 8 ^ j := by rw [← mul_pow]; norm_num
      push_cast
      rw [hpos, hw, h3, ← h83]
      ring"""
ind=lambda ls:['  '+l for l in ls]
numhave=h[inum][:-len('erdos_1050__h1_v2__h2__h1')]+'by'
out=h[:inum]+pc['shared']+pc['cmt']+[numhave]+ind(pc['numbody'])+h[inum+1:ikey+1]+newkey.split('\n')+h[iw3:]
src='\n'.join(out)+'\n'
open('h2-direct.lean','w').write(src)
import api
st=open('/home/claude/open_proof_network_graph/targets/erdos-1050/nodes/erdos-1050--h1-v2--h2/Statement.lean').read()
print('header ok', src.startswith(st.split(':= by\n  sorry')[0]), 'sorry' in src, 'erdos_1050__h1_v2__h2__h1' in src)
s,a=api.check(src.replace('\ntheorem ','\n#count_heartbeats in\ntheorem ',1),'erdos-1050--h1-v2--h2')
print(s,a.get('okay'),[w['code'] for w in a.get('lint',[])] if isinstance(a,dict) else a)
if isinstance(a,dict):
    for e in a['result']['lean_messages']['errors'][:4]: print(e[:500],'\n...',e[e.rfind('⊢'):][:1200] if len(e)>500 else '','\n=====')
    print([i[:120] for i in a['result']['lean_messages']['infos'] if 'heartbeats' in i], a['result'].get('timings'))
