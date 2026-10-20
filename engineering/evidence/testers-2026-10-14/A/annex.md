Source: W. van Doorn and Q. Tang, "Consecutive integers free of certain prime factors", arXiv:2606.19863 (2026), and its Lean 4.28 development at https://github.com/Woett/ChatGPT-s-note-on-Erdos451 (file `ErdosProblem451.lean`, theorem `main_theorem`, resting on one `axiom bhp`, Baker–Harman–Pintz).

This node is `¬BHP ∨ main_theorem` with their definitions unfolded (theta = 21/40, `Pprod k n = ∏_{i=1..k} (n - i)`, `primeCard`). Their `main_theorem` is proved (lines 4665–4689 of the file) by splitting the range 2k < n ≤ exp(log²k / (20 log log k)) into four cases at the cut points k^(2-θ)/2, k²/log²k and k^(2+θ)/2, and applying four lemmas, each of which takes BHP (`obtain ⟨C, hC, kb, hb⟩ := bhp`, directly or through `exists_prime_in_window`):

1. `case_small` (line 3837): 2k < n ≤ k^(2-θ)/2. Uses `exists_prime_in_window` (BHP applied at a shifted base point) and a residue argument.
2. `case_medium` (line 4268): k^(2-θ)/2 < n ≤ k²/log²k. A fibre-counting bound on the bad set (`med_card_bound`, `med_rhs_le`) beaten by BHP's prime count, finished by `konyagin_finish`.
3. `case_mediumlarge` (line 4041): k²/log²k < n ≤ k^(2+θ)/2. Same shape via `ml_card_bound`, `ml_rhs_le`.
4. `case_large` (line 4623): k^(2+θ)/2 < n ≤ exp(log²k/(20 log log k)). The Konyagin step: `large_card_raw` (from `konyagin_application`, which rests on their proof of `konyagin_thm`, the lattice/successive-minima part of the file, lines ~135–3410), `large_asym`, `large_r_data`, then `konyagin_finish`.

The skeleton states each case as `¬BHP ∨ case_i` (so that no hole needs BHP itself as a witness) and proves the assembly: if any hole gives ¬BHP, take the left disjunct; otherwise combine the four cases by the same three `by_cases` on n as `main_theorem`. No single hole implies the node: each covers one range of n only.

What is my reading, not checked by anyone: that the four case lemmas' statements in the file are exactly as transcribed here (the skeleton restates them with θ and Pprod unfolded and the cut points written as real powers), and that each lemma's proof in the file uses only BHP and earlier lemmas (the file's `#print axioms main_theorem` is their claim; I did not run their file at 4.28). Porting each case's proof to Lean 4.33.1/current Mathlib is what remains; the largest is `h_large`, which needs `konyagin_thm`.
