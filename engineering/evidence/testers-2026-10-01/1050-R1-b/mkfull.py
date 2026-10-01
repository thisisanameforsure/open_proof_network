import sys
qb=open('q_body.lean').read().rstrip('\n').split('\n')
rb=open('r_body.lean').read().rstrip('\n').split('\n')
P=lambda s,k:"∏ l ∈ %s.erase %s, (1 - (2 : ℝ) ^ ((l : ℤ) - (%s : ℤ)))"%(s,k,k)
common1=qb[0:27]
geo=qb[71:104]
assert qb[104].strip()=='intro n hn' and qb[106].startswith('  obtain ⟨α, hα⟩ : ') and qb[123].startswith('  obtain ⟨D, hD⟩')
polystmt=qb[106][len('  obtain ⟨α, hα⟩ : '):]
assert polystmt.endswith(' := by')
hpoly=["  have hpoly : ∀ n : ℕ, 1 ≤ n → "+polystmt,"    intro n hn"]+qb[107:123]
rest=qb[123:]
V=lambda m,s:"∑ k ∈ %s, (((2 : ℝ) ^ k) ^ (%s))⁻¹ / %s"%(s,m,P(s,'k'))
new=f"""  -- the recursion h_e(s) = h_e(s minus a) + y_a h_(e-1)(s), for any weight f
  have hrec : ∀ (s : Finset ℕ) (a : ℕ) (f : ℕ → ℝ), a ∈ s → ∑ k ∈ s, (2 : ℝ) ^ k * f k / {P('s','k')} = ∑ k ∈ s.erase a, (2 : ℝ) ^ k * f k / {P('(s.erase a)','k')} + (2 : ℝ) ^ a * ∑ k ∈ s, f k / {P('s','k')} := by
    intro s a f ha
    rw [← Finset.add_sum_erase s (fun k => f k / {P('s','k')}) ha, ← Finset.add_sum_erase s (fun k => (2 : ℝ) ^ k * f k / {P('s','k')}) ha, mul_add, Finset.mul_sum, add_left_comm, ← Finset.sum_add_distrib]
    congr 1
    · ring
    · refine Finset.sum_congr rfl (fun k hk => ?_)
      have hka : k ≠ a := Finset.ne_of_mem_erase hk
      have hmem : a ∈ s.erase k := Finset.mem_erase.mpr ⟨Ne.symm hka, ha⟩
      have hsplit := Finset.mul_prod_erase (s.erase k) (fun l => (1 - (2 : ℝ) ^ ((l : ℤ) - (k : ℤ)))) hmem
      rw [Finset.erase_right_comm] at hsplit
      rw [← hsplit]
      have hρ : (1 - (2 : ℝ) ^ ((a : ℤ) - (k : ℤ))) ≠ 0 := by
        intro h1
        have h2 : (2 : ℝ) ^ ((a : ℤ) - (k : ℤ)) = 2 ^ (0 : ℤ) := by rw [zpow_zero]; linarith
        have h3 := zpow_right_injective₀ (by norm_num : (0 : ℝ) < 2) (by norm_num) h2
        omega
      have hq : (1 - (2 : ℝ) ^ ((a : ℤ) - (k : ℤ))) * (1 - (2 : ℝ) ^ ((a : ℤ) - (k : ℤ)))⁻¹ = 1 := mul_inv_cancel₀ hρ
      have hak : (2 : ℝ) ^ a = (2 : ℝ) ^ ((a : ℤ) - (k : ℤ)) * 2 ^ k := by
        rw [zpow_sub₀ two_ne_zero, zpow_natCast, zpow_natCast]
        field_simp
      simp only [div_eq_mul_inv, mul_inv]
      rw [hak]
      linear_combination ((2 : ℝ) ^ k * f k * (∏ l ∈ (s.erase a).erase k, (1 - (2 : ℝ) ^ ((l : ℤ) - (k : ℤ))))⁻¹) * hq
  -- (L) complete homogeneous sums at the nodes 2^k are integers
  have hW : ∀ N : ℕ, ∀ (s : Finset ℕ) (e : ℕ), s.card + e = N → ∃ z : ℤ, (z : ℝ) = ∑ k ∈ s, ((2 : ℝ) ^ k) ^ e / {P('s','k')} := by
    intro N
    induction N with
    | zero =>
      intro s e h
      have hs : s = ∅ := Finset.card_eq_zero.mp (by omega)
      subst hs
      exact ⟨0, by simp⟩
    | succ N ih =>
      intro s e h
      rcases s.eq_empty_or_nonempty with rfl | hs
      · exact ⟨0, by simp⟩
      rcases Nat.eq_zero_or_pos e with rfl | he
      · exact ⟨1, by rw [Int.cast_one]; exact (h0 s hs).symm.trans (Finset.sum_congr rfl (fun k _ => by rw [pow_zero]))⟩
      obtain ⟨e', rfl⟩ : ∃ e', e = e' + 1 := ⟨e - 1, by omega⟩
      obtain ⟨a, ha⟩ := hs
      obtain ⟨z1, hz1⟩ := ih (s.erase a) (e' + 1) (by rw [Finset.card_erase_of_mem ha]; have := Finset.card_pos.mpr ⟨a, ha⟩; omega)
      obtain ⟨z2, hz2⟩ := ih s e' (by omega)
      refine ⟨z1 + 2 ^ a * z2, ?_⟩
      have hr := hrec s a (fun k => ((2 : ℝ) ^ k) ^ e') ha
      simp only [← pow_succ'] at hr
      push_cast
      rw [hz1, hz2]
      exact hr.symm
  -- (L-) and they vanish in negative degree above minus the number of nodes
  have hV : ∀ m : ℕ, ∀ s : Finset ℕ, m + 1 < s.card → {V('m + 1','s')} = 0 := by
    intro m
    induction m with
    | zero =>
      intro s hs
      obtain ⟨a, ha⟩ : s.Nonempty := Finset.card_pos.mp (by omega)
      have hne : (s.erase a).Nonempty := Finset.card_pos.mp (by rw [Finset.card_erase_of_mem ha]; omega)
      have h := hrec s a (fun k => (((2 : ℝ) ^ k) ^ (0 + 1))⁻¹) ha
      have e : ∀ k : ℕ, (2 : ℝ) ^ k * (((2 : ℝ) ^ k) ^ (0 + 1))⁻¹ = 1 := fun k => by
        rw [zero_add, pow_one]; exact mul_inv_cancel₀ (by positivity)
      simp only [e] at h
      rw [h0 s ⟨a, ha⟩, h0 _ hne] at h
      have h2a : (2 : ℝ) ^ a ≠ 0 := by positivity
      rcases mul_eq_zero.mp (show (2 : ℝ) ^ a * ({V('0 + 1','s')}) = 0 by linarith) with h5 | h5
      · exact absurd h5 h2a
      · exact h5
    | succ m ih =>
      intro s hs
      obtain ⟨a, ha⟩ : s.Nonempty := Finset.card_pos.mp (by omega)
      have h := hrec s a (fun k => (((2 : ℝ) ^ k) ^ (m + 1 + 1))⁻¹) ha
      have e : ∀ k : ℕ, (2 : ℝ) ^ k * (((2 : ℝ) ^ k) ^ (m + 1 + 1))⁻¹ = (((2 : ℝ) ^ k) ^ (m + 1))⁻¹ := fun k => by
        rw [pow_succ' _ (m + 1), mul_inv, ← mul_assoc, mul_inv_cancel₀ (by positivity), one_mul]
      simp only [e] at h
      rw [ih s (by omega), ih (s.erase a) (by rw [Finset.card_erase_of_mem ha]; omega)] at h
      have h2a : (2 : ℝ) ^ a ≠ 0 := by positivity
      rcases mul_eq_zero.mp (show (2 : ℝ) ^ a * ({V('m + 1 + 1','s')}) = 0 by linarith) with h5 | h5
      · exact absurd h5 h2a
      · exact h5"""
c="(8 / 3 : ℝ)"
Dk=P('(Finset.Icc 1 n)','k')
T=f"(({c} * (2 : ℝ) ^ k) ^ j * ((({c} * (2 : ℝ) ^ k) ^ i)⁻¹) / {Dk})"
newkey=f"""      intro n hn i hi1 hi2
      obtain ⟨α, hα⟩ := hpoly n hn
      have hA : ∀ k : ℕ, ∏ t ∈ Finset.Icc 1 (n - 1), (1 - {c} * (2 : ℝ) ^ (t + k)) = ∑ j ∈ Finset.range n, (α j : ℝ) * ({c} * 2 ^ k) ^ j := by
        intro k
        rw [← hα]
        refine Finset.prod_congr rfl (fun t _ => ?_)
        rw [pow_add]; ring
      simp only [hA]
      have e1 : ∑ k ∈ Finset.Icc 1 n, (-(∑ j ∈ Finset.range n, (α j : ℝ) * ({c} * 2 ^ k) ^ j) / {Dk}) * ((({c} * (2 : ℝ) ^ k) ^ i)⁻¹) = ∑ j ∈ Finset.range n, ∑ k ∈ Finset.Icc 1 n, (-(α j : ℝ)) * {T} := by
        rw [Finset.sum_comm]
        refine Finset.sum_congr rfl (fun k _ => ?_)
        rw [neg_div, neg_mul, Finset.sum_div, Finset.sum_mul, ← Finset.sum_neg_distrib]
        refine Finset.sum_congr rfl (fun j _ => ?_)
        ring
      rw [e1, Finset.mul_sum]
      refine hsumZ _ _ (fun j hj => ?_)
      have hj' := Finset.mem_range.mp hj
      rw [← Finset.mul_sum]
      have hcX : ∀ k : ℕ, ({c} * (2 : ℝ) ^ k) ≠ 0 := fun k => by positivity
      rcases lt_or_ge j i with hji | hji
      · refine ⟨0, ?_⟩
        have hvan : ∑ k ∈ Finset.Icc 1 n, {T} = ({c} ^ (i - j))⁻¹ * ∑ k ∈ Finset.Icc 1 n, (((2 : ℝ) ^ k) ^ (i - j - 1 + 1))⁻¹ / {Dk} := by
          rw [Finset.mul_sum]
          refine Finset.sum_congr rfl (fun k _ => ?_)
          have hk : ({c} * (2 : ℝ) ^ k) ^ j * ((({c} * (2 : ℝ) ^ k) ^ i)⁻¹) = ({c} ^ (i - j))⁻¹ * (((2 : ℝ) ^ k) ^ (i - j))⁻¹ := by
            rw [show ({c} * (2 : ℝ) ^ k) ^ i = ({c} * (2 : ℝ) ^ k) ^ j * ({c} * (2 : ℝ) ^ k) ^ (i - j) from by rw [← pow_add]; congr 1; omega,
              mul_inv, ← mul_assoc, mul_inv_cancel₀ (pow_ne_zero _ (hcX k)), one_mul, mul_pow, mul_inv]
          rw [hk, mul_div_assoc, show i - j - 1 + 1 = i - j by omega]
        rw [hvan, hV (i - j - 1) (Finset.Icc 1 n) (by rw [Nat.card_Icc]; omega)]
        simp
      · obtain ⟨w, hw⟩ := hW _ (Finset.Icc 1 n) (j - i) rfl
        refine ⟨-(α j) * 3 ^ (n - 1 - j) * 8 ^ (j - i) * w, ?_⟩
        have hpos : ∑ k ∈ Finset.Icc 1 n, {T} = {c} ^ (j - i) * ∑ k ∈ Finset.Icc 1 n, ((2 : ℝ) ^ k) ^ (j - i) / {Dk} := by
          rw [Finset.mul_sum]
          refine Finset.sum_congr rfl (fun k _ => ?_)
          have hk : ({c} * (2 : ℝ) ^ k) ^ j * ((({c} * (2 : ℝ) ^ k) ^ i)⁻¹) = {c} ^ (j - i) * ((2 : ℝ) ^ k) ^ (j - i) := by
            rw [show ({c} * (2 : ℝ) ^ k) ^ j = ({c} * (2 : ℝ) ^ k) ^ (j - i) * ({c} * (2 : ℝ) ^ k) ^ i from by rw [← pow_add]; congr 1; omega,
              mul_assoc, mul_inv_cancel₀ (pow_ne_zero _ (hcX k)), mul_one, mul_pow]
          rw [hk, mul_div_assoc]
        have h3 : (3 : ℝ) ^ (n - 1 - i) = 3 ^ (n - 1 - j) * 3 ^ (j - i) := by rw [← pow_add]; congr 1; omega
        have h83 : {c} ^ (j - i) * 3 ^ (j - i) = 8 ^ (j - i) := by rw [← mul_pow]; norm_num
        push_cast
        rw [hpos, hw, h3, ← h83]
        ring"""
p1=open('p1.lean').read().rstrip('\n').split('\n')
ir=[j for j,l in enumerate(p1) if l.strip().startswith('have residue_integral')][0]
ip=[j for j,l in enumerate(p1) if l.strip().startswith('have polypart_integral')][0]
ik=[j for j,l in enumerate(p1) if l.strip().startswith('have key')][0]
iw=[j for j,l in enumerate(p1) if l.strip().startswith('have hW3')][0]
assert ip==ir+1
ind=lambda ls:['  '+l for l in ls]
out=p1[:ir]+common1+new.split('\n')+geo+hpoly
shared=common1+new.split('\n')+geo+hpoly
npre=len(out)
out+= [p1[ir][:-len('sorry')]+'by']+ind(rb)
out+= [p1[ip][:-len('sorry')]+'by']+ind(['  intro n hn','  obtain ⟨α, hα⟩ := hpoly n hn']+rest)
out+= p1[ip+1:ik+1]
out+= newkey.split('\n') if len(sys.argv)<2 else p1[ik+1:iw]
out+= p1[iw:]
open('full2.lean','w').write('\n'.join(out)+'\n')

import json
json.dump({'shared':shared,'numbody':out[npre:],'cmt':p1[ir-4:ir]},open('pieces.json','w'))
