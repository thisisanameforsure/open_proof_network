# Curator C log (Green's open problems 24, 25, 27, 31, 35, 38; answer-shaped)

- 2026-11-25T13:48Z — started. Read the brief, the eight rows, and the six registry files in full
  (24, 25, 27, 31, 35, 38 at d8d031d4). Reference layouts read: abc, green-36, green-29, erdos-30.
  Library definitions located: `≪` (Analysis/Asymptotics/Basic), `HasNoUniqueRepresentation`,
  `IsSidon`, `maxSidonSubsetCard` (Combinatorics/Basic), `restrictedSumset`
  (Combinatorics/Additive/RestrictedSumset), `𝔽₇`/`𝔽₂` (Data/ZMod/Fp).
- 2026-11-25T13:50Z — sources: Green's *100 open problems* PDF fetched and text-extracted (pypdf);
  Problems 24, 25, 27, 31, 35, 38 read in full. erdosproblems.com/30 and /484 refused (HTTP 403).
  arXiv abstracts read: 2210.16437 (White, L2 autoconvolution), 2610.09349 (Hou–Yang, m(p)),
  2605.05193 (Grok note, constant unreadable). Searches: Shannon capacity C7 upper bound (no
  improvement on Lovász), Sidon upper constant after HZ26 (none found).
- 2026-11-25T13:52Z — decisions:
  - 24 `variants.conjecture` (`gamma = 1/3`): import as stated; the row never used the answer.
    Green: "It seems likely that the answer is (1/3 + o(1))n2, but this is not known."
  - 25 `green_25.lower`: import adapted, `∃ L`; open per Green ("all that is known").
  - 25 `green_25.upper`: DECLINED; existence form follows from the file's own solved
    `upper_pow_23_40`.
  - 27 `green_27.upper`: import adapted, `∃ U` (= m(p) = o(log² p)); open per HY26.
  - 31 `green_31.lower`: import adapted, `∃ L`; open per Green.
  - 31 `green_31.upper`: import adapted, `∃ U`; implied by Erdős #30 (live erdos-30).
  - 35 `green_35.lower`: DECLINED; existence form ⟺ `√(4/7) < c 2 ∨ 0.64 < c ∞`, first disjunct
    known (White, CMB 2024: c2² ≥ 0.574636 > 4/7).
  - 38 `green_38.upper`: import adapted, `∃ U` (= Θ(C7) < ϑ(C7)); "Set" refusal spurious.
- 2026-11-25T13:55Z — ports written: Local.lean per file (placeholder answers removed), library
  ports copied from graph-ref (green-2: RestrictedSumset; erdos-30: CombinatoricsBasic, APBasic),
  hand ports of Data/ZMod/Fp and Analysis/Asymptotics/Basic. Script check: every port line occurs
  in its source file; no sorry/axiom/opaque in any defs file (port notes reworded to avoid the word).
- 2026-11-25T13:57:24Z — check 24: POST /check, log_id 01M89FYDC8D5A9BS7RVBN7ZJYG, errors [] (1 sorry warning).
- 2026-11-25T13:57:36Z — check 25.lower: log_id 01M89FYT2GEMC1PHR4GNFGM7J1, errors [].
- 2026-11-25T13:57:38Z — check 27.upper: log_id 01M89FZ0X8BWCNTEJW6TT2YQ07, errors [].
- 2026-11-25T13:57:45Z — check 31.lower: log_id 01M89FZ5SG3Q77DPZEH44168T6, errors [].
- 2026-11-25T13:57:50Z — check 31.upper: log_id 01M89G0HQRFY54S8QBA0PG6QD5, errors [].
- 2026-11-25T13:58:35Z — check 38.upper: log_id 01M89G0JQ0E8RN2VTW9BR2JMRV, errors [].
- 2026-11-25T13:59:30Z — combined transcription check, log_id 01M89G2J68W1KRJE47ZSYP2P1Q,
  errors []: `(∃ a, Reg a) ↔ graph statement` by Iff.rfl for 25.lower, 27.upper, 31.lower,
  31.upper, 38.upper (registry bodies copied verbatim); 25.upper decline reduction from
  `upper_pow_23_40` proved; 35.lower decline reduction from `√(4/7) < c 2` proved. Script confirmed
  the checked copies equal the Statement.lean theorems. Seven /check calls in all.
- 2026-11-25T14:05Z — CURATION.md written for all eight rows. Done.
