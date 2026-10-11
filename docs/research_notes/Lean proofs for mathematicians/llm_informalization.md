# LLM-based informalization of Lean proofs (formal to informal), as of October 2026

Scope note: researched 2026-10-03. "Measured" means a number reported from an experiment in the cited source; "claim" means an assertion without a reported measurement. Several 2026 arXiv items were seen only at abstract level; that is flagged where it matters.

## 1. Papers and systems that turn Lean proofs (not only statements) into natural language

### Takeaway
Only two published methods target *proof* informalization directly and report any evaluation: Herald (ICLR 2025, line-by-line translation using tactic states, evaluated qualitatively for proofs) and Hattori, Matsuzaki and Fujiwara (INLG 2025, per-step templated informalization plus recursive summarization along the proof's structure, with a small human evaluation). Most named systems (Aristotle, Gauss, Kimina, DeepSeek-Prover, Goedel-Prover, AlphaProof) go informal to formal; their informal text is a *plan written before* the Lean, not an explanation derived from it. Human write-ups of AI Lean proofs (Erdős #728, Sendov) were done by people, with AI assistance.

### Cited Findings
**Proof informalization methods**
- Herald (Gao et al., arXiv 2410.10878, ICLR 2025) builds NL–FL pairs from Mathlib 4: about 580k statement pairs and 45k proof pairs (the paper's conclusion says "44k NL-FL theorem pairs"; the abstract says 45k, a small internal inconsistency). — [Herald, arXiv 2410.10878](https://arxiv.org/abs/2410.10878)
- Herald's proof method: extract proof lines with the Lean-jixia static analyser, "translat[e] each line of the formal proof into natural language", then combine the line translations into a complete informal proof. Prompts carry the formal statement, its informal statement, tactic information, and "the proof state before and after each proof step". Dependencies are informalized before the theorems that use them (hierarchical order). — [Herald §3.1](https://arxiv.org/pdf/2410.10878)
- Herald restricts proof informalization to *tactic-style* proofs: term-style proofs "often present a series of formal theorems without a clear expression of logical reasoning", so they were not translated. — [Herald §3.1](https://arxiv.org/pdf/2410.10878)
- Herald adds human-written explanations of "the logical structure inherent in each type of tactic" to the prompts, because a major LLM limitation is "lack of understanding of the logical relationships between the proof steps and the goal". — [Herald §3.1](https://arxiv.org/pdf/2410.10878)
- Herald's own qualitative assessment of its proof output (no number given): the step-wise translation "faithfully reflects the proof strategy used in the formal proof", but "the level of detail in the translated proofs is closer to formal language rather than natural language", and Mathlib identifiers leak into the LaTeX (e.g. `treesOfNumNodesEq`, `antidiagonal`) even though the prompt forbids this; the authors expect bad statement translations to be inherited by the proof translations. — [Herald §4.2 and App. E](https://arxiv.org/pdf/2410.10878)
- Hattori, Matsuzaki, Fujiwara, "Natural Language Translation of Formal Proofs through Informalization of Proof Steps and Recursive Summarization along Proof Structure" (arXiv 2509.09726, 10 Sept 2025, INLG 2025). Method: (1) rule-based *templates* per tactic plus a "premise library" (natural-language descriptions of the definitions and lemmas used) to informalize each proof step from the tactic and the before/after proof state; (2) dependency-structure analysis, then *recursive summarization* of semantically coherent units into a readable proof. Model: GPT-4.1-mini (temperature 0.4 for steps, 1.0 for summaries). — [arXiv 2509.09726](https://arxiv.org/abs/2509.09726)
- The same paper notes that templated step generation was preferred over Herald's free-form explanation "to directly control the form of step-wise informalization", and that recursive summarization (rather than concatenating steps) is what makes the output read like a human proof. — [arXiv 2509.09726 §2](https://arxiv.org/pdf/2509.09726)
- Older approach still cited: Patrick Massot's Lean-bavard / controlled-natural-language renderings, used with first-year undergraduates; discussed on Lean Zulip in 2020–2021 with no quantitative results. — [Lean Zulip archive, "Natural language translation"](https://leanprover-community.github.io/archive/stream/113488-general/topic/Natural.20language.20translation.html)
- Lean Finder (ICLR 2026) used GPT-4o to synthesize informal descriptions of Lean statements and proof transitions for search, with "context information" supplied per statement. This is informalization for retrieval, not for reading. — [Lean Finder, arXiv 2510.15940](https://arxiv.org/abs/2510.15940)

**Blueprint and traceability tooling (no LLM translation)**
- LeanArchitect (Zhu, Monticone, Avigad, Welleck; arXiv 2601.22554, 30 Jan 2026): a Lean package where declarations carry blueprint annotations (LaTeX statement, informal proof sketch with explicit references to earlier nodes); it infers dependency and proof status from the Lean environment and generates the blueprint, "eliminat[ing] duplication between formal and informal representations". It does not generate the prose with an LLM. — [arXiv 2601.22554](https://arxiv.org/abs/2601.22554)
- LeanMarathon (Zhang et al., arXiv 2606.05400, 2026): each blueprint node "keeps its LaTeX prose beside its Lean type", and a CI verifier enforces "two-way parity" between LaTeX `\cref` citations and Lean dependencies so the "natural-language and formal graphs cannot silently diverge". Multi-resolution back-translation (overview / outline / full derivation) is stated as a *possibility*, not implemented or measured. — [LeanMarathon, arXiv 2606.05400](https://arxiv.org/html/2606.05400v1)

**Prover systems: informal text precedes the Lean**
- Aristotle (Harmonic, arXiv 2510.01346, 1 Oct 2025) combines Lean proof search, an informal reasoning system that "generates and formalizes lemmas", and a geometry solver; 5 of 6 IMO 2025 problems with Lean proofs. The informal lemma text exists because it is the plan that was formalized. — [Aristotle, arXiv 2510.01346](https://arxiv.org/abs/2510.01346)
- Kimina-Prover Preview (arXiv 2504.11354, Apr 2025) interleaves informal reasoning and Lean snippets in a thinking block; to keep them consistent it required "≥60% of generated code snippets (from the thinking block) be reused in the final proof", and used ~20K Claude 3.7 Sonnet–synthesized examples to align informal and formal steps. This is the only quantitative informal–formal coupling rule found among prover systems. — [Kimina-Prover, arXiv 2504.11354](https://arxiv.org/pdf/2504.11354)
- Math Inc's Gauss completed the Strong Prime Number Theorem project in ~3 weeks (announced Sept 2025): ~25,000 lines of Lean, 1,100+ theorems and definitions; humans supplied the high-level blueprint and reviewed key lemmas. — [math-inc/strongpnt](https://github.com/math-inc/strongpnt)
- Jesse Michael Han (Math Inc), on that artifact: "there is no single human who is really familiar with this artifact." — [X post, Sept 2025](https://x.com/jessemhan/status/1966379609932673097)

**Human write-ups of AI-produced Lean proofs**
- Erdős #728 (first Erdős problem regarded as resolved essentially autonomously by AI; GPT-5.2 Pro plus Aristotle, operated by Kevin Barreto, Jan 2026). Nat Sothanaphan wrote the informal account "for wider accessibility" (arXiv 2601.07421, 12 Jan 2026, revised 26 Jan 2026); Boris Alexeev used Aristotle to simplify the proof; Tao suggested ideas and literature. — [arXiv 2601.07421](https://arxiv.org/abs/2601.07421)
- In the Erdős #728 discussion, a participant ran the Lean proof through ChatGPT to rewrite it in natural language; after further conversation, gaps in the original were filled, but the exposition was still "somewhat clunky and 'AI' in feel" (search-result summary of Tao's Mathstodon thread; the thread itself could not be fetched). — [Tao, Mathstodon, Jan 2026](https://mathstodon.xyz/@tao/115855840223258103)
- Sendov's conjecture (Lech Mazur, AI-assisted, verified in Lean; original formalization ~90,000 lines). Tao's digestion (12 Aug 2026) took "several days (with heavy AI assistance)" plus pen and paper "to place the proof in proper context with previous literature and to simplify and streamline the argument to highlight the main ideas"; he then had an AI agent re-formalize *his* digested argument in ~15,000 lines. — [Tao, "A digestion of the proof of Sendov's conjecture"](https://terrytao.wordpress.com/2026/08/12/a-digestion-of-the-proof-of-sendovs-conjecture/)

### Inferences
- The Sendov case is the strongest precedent for the use case: the readable proof came from a human-led digestion *and then* a new, shorter formalization keyed to it, rather than from informalizing the original 90k-line Lean. A faithful line-by-line informalization of an agent-written proof inherits the agent's structure, including detours.
- No system found produces a step-by-step informal proof whose every step is keyed by identifier to a Lean tactic or declaration *as a published, evaluated output*. Herald and Hattori et al. have that alignment internally (step → informal sentence) but then merge or summarize it away.

### Gaps
- No public description found of informal outputs from AlphaProof (Nature, 2025), Google DeepMind's or OpenAI's 2025–2026 olympiad/Erdős work, DeepSeek-Prover-V2 or Goedel-Prover-V2 that are *derived from* a finished Lean proof. Their natural-language olympiad solutions were not informalizations of Lean (not verified here with a fetched source).
- "MMA" (multilingual informal–formal dataset) and Lean Workbook were not re-checked; both are informal to formal datasets in this author's understanding, unverified this session.
- Harmonic, Math Inc and Axiom product documentation on "explain this proof" features was not found.

## 2. Measured faithfulness: how often does informal text misstate what the Lean proves?

### Takeaway
For *proofs*, the only measured numbers are small and single-annotator: Hattori et al. report 89% of 1,242 informalized proof steps correct with templates and a premise library (5% misinformation), falling to ~54% correct without templates, and summaries capturing 86% of key points on 17 proofs. No study measures the false-pass rate of back-translation or LLM judges on *proof* informalizations. The statement-level evidence (back-translation passes wrong about a third of the time) is the closest proxy and has not been tested on proofs.

### Cited Findings
- Hattori et al., step level (measured; 1,242 steps from 38 formal proofs, graded manually by the first author): with templates and premise library 89.05% correct, 5.15% misinformation, 1.50% insufficient information, 3.87% unnecessary mention, 0.40% untranslated formal expression. Templates without premise library: 83.09% correct, 8.05% misinformation. Without templates: 53.95% / 53.22% correct, with insufficient information ~18.5% and unnecessary mentions ~24.4%. Differences significant by McNemar's test (α = 0.05) except between the two no-template settings. — [arXiv 2509.09726, Table 1](https://arxiv.org/pdf/2509.09726)
- Same paper, counter-intuitive finding: misinformation *rises* with templates (5.15% vs 2.50%) because the templated output mentions more specific variables, hypotheses and cited theorems, i.e. more content that can be wrong. — [arXiv 2509.09726 §5.2](https://arxiv.org/pdf/2509.09726)
- Untranslated formal notation (e.g. `sInf`, `x n` for xₙ) persisted at ~0.3–0.9% of steps regardless of method. — [arXiv 2509.09726 §5.2](https://arxiv.org/pdf/2509.09726)
- Hattori et al., proof level (measured; 17 calculus proofs, ~6.4 key-point criteria each, three-point scale): recursive summarization score 0.857 (87 captured, 11 partial, 10 missed); without recursive summarization 0.833. Qualitatively, without recursive summarization "four [of 17] included reasoning not in the original proof and/or contained substantial logical inconsistencies"; with it, none showed "significant deviations". — [arXiv 2509.09726, Table 2 and §5.3](https://arxiv.org/pdf/2509.09726)
- Statement-level back-translation audit (measured): Herald's validation pipeline (compile + back-translate with InternLM2-Math-Plus-7B + NLI check with DeepSeek Chat v2.5) passed 151 of 185 ProofNet statements; human experts found 101 correct, 24 minor errors, 26 major errors, i.e. ~33% of passes wrong (InternLM baseline: 72 passed, 42 correct). — [Herald, Appendix D, Table 4](https://arxiv.org/pdf/2410.10878)
- FormalAlign (ICLR 2025) trains an alignment scorer; alignment-selection score 99.21% vs GPT-4's 88.91% on FormL-Basic, but only 66.39% vs 64.34% on MiniF2F-Valid. Statement-level only. — [FormalAlign, arXiv 2410.10135](https://arxiv.org/abs/2410.10135)
- FaithSieve (Wang, Dai, Wu, Wen; arXiv 2608.26310, 26 Aug 2026) evaluates *informal* proofs by decomposing them into reasoning units, formalizing typed obligations, and admitting formal evidence only when the formal statement "faithfully preserves the context, objects, and logical form of the original claim". First-error localization: 81.43% vs 72.29% baseline on ProofLoc-Olympiad (350 problems), 84.5% vs 75.0% on ProofLoc-University (200). — [FaithSieve, arXiv 2608.26310](https://arxiv.org/abs/2608.26310)
- Fine-grained evaluation of NL proofs (arXiv 2510.13888): among cases where evaluators disagreed most, 80% were proofs with "sophisticated presentation but fundamental logical errors" — evidence that polished prose fools judges. — [arXiv 2510.13888](https://arxiv.org/pdf/2510.13888)
- Proof-route faithfulness in the reverse direction: "Does the Proof Prove It That Way?" (Mao et al., arXiv 2608.15432, 15 Aug 2026) defines five necessary conditions for a formal proof to follow the informal argument's route (Euclid's *Elements* I–III); its Pistis system was preferred 2.89× by blinded human reviewers and 5.2× by an LLM judge over prior work. The gap between human and LLM-judge preference ratios is itself evidence that LLM judges and humans weigh faithfulness differently. — [arXiv 2608.15432](https://arxiv.org/abs/2608.15432)
- ProofFlow (Cabral et al., arXiv 2510.15981, Oct 2025): structural fidelity measured by ProofScore on 184 undergraduate problems: DAG-first lemma-based formalization 0.545 vs whole-proof 0.123 vs step-proof 0.072 (informal to formal direction). — [ProofFlow, arXiv 2510.15981](https://arxiv.org/abs/2510.15981)
- Erdős AI-contributions wiki (Tao et al.) records AI outputs flagged "Incorrect claim made" (e.g. #11, Jan 2026), "Incorrect proof found" (#51, Jan 2026) and "Argument with major gaps" (#358, #963, #1041, #388), and encourages Lean formalization of AI proofs; it does not record informalization errors as a separate category. — [teorth/erdosproblems wiki](https://github.com/teorth/erdosproblems/wiki/AI-contributions-to-Erd%C5%91s-problems)
- Project's own prior note records AlphaProof Nexus (2026-05-21; 9 of 353 open Erdős problems) as having two proofs that used "natural density" where "lower density" was meant, with informal statements amended afterwards — a statement-level mismatch between informal claim and formal content. (Secondary: from this repo's research note, not re-fetched.) — [docs/research_math_and_ai_2026-09.html](../../research_math_and_ai_2026-09.html)

### Inferences
- A rough working figure for proof informalization with a good pipeline is "about 1 in 10–20 steps wrong or misleading" (5% misinformation plus ~5% other defects), from one small calculus study with one grader on a mini model. Research-level, agent-written proofs (long, automation-heavy, `simp`/`omega`/`nlinarith` closing steps) are likely worse; nothing measures them.
- Back-translation as a check for proof informalizations would inherit the statement-level weakness (≈1/3 false pass) and probably worse, since a proof has many more claims per item and a judge compares prose to prose.
- The more specific the explanation (naming hypotheses, lemmas), the more checkable it is and the more it can be wrong (Hattori's misinformation result). Specificity should be paired with a mechanical check, not avoided.

### Gaps
- No measurement of LLM-judge or back-translation false-pass rates on *proof* informalizations was found.
- No study grades informalizations of research-level or agent-written Lean proofs by mathematicians.
- No inter-annotator agreement exists for the only proof-level study (single grader).

## 3. Techniques that improve faithfulness and traceability

### Takeaway
The techniques with evidence are: generate per step from the tactic and the before/after proof state (not the source text alone); constrain the step output with per-tactic templates and supply natural-language descriptions of every cited lemma (a "premise library"); summarize recursively along the proof's dependency structure rather than all at once; and keep prose and Lean as paired nodes in a DAG checked by CI (blueprint parity). Re-formalizing informal claims to check them (FaithSieve) works for evaluation but only when a separate faithfulness gate guards the re-formalized statements.

### Cited Findings
- Tactic-state conditioning: both Herald and Hattori et al. feed the proof state before and after each step; Herald reports this "helps the LLM understand how each proof step contributes to the overall proof". — [Herald §3.1](https://arxiv.org/pdf/2410.10878); [arXiv 2509.09726](https://arxiv.org/abs/2509.09726)
- Templates + premise library raise step accuracy from ~54% to ~89%; the premise library alone (without templates) gives no significant gain; templates plus premise library add ~6 points over templates alone. — [arXiv 2509.09726, Table 1](https://arxiv.org/pdf/2509.09726)
- Recursive summarization along the dependency structure keeps each LLM input small; the authors attribute fewer hallucinations to this ("the limited input window of the LLM likely contributes to hallucinations"). — [arXiv 2509.09726 §5.3](https://arxiv.org/pdf/2509.09726)
- Dependency-first informalization: Herald informalizes dependencies before dependents so each translation can cite the already-translated lemma. — [Herald](https://arxiv.org/abs/2410.10878)
- Blueprint parity as a traceability guarantee: LeanMarathon's CI verifier checks that informal `\cref` edges and Lean dependencies agree in both directions. — [arXiv 2606.05400](https://arxiv.org/html/2606.05400v1)
- Lean-environment-derived blueprints: LeanArchitect reads dependency and proof status from Lean and generates the blueprint, and its case study "exposes latent inconsistencies". — [arXiv 2601.22554](https://arxiv.org/abs/2601.22554)
- Coupling constraint: Kimina's ≥60% snippet-reuse rule forces the informal reasoning and the final Lean to share code. — [arXiv 2504.11354](https://arxiv.org/pdf/2504.11354)
- Re-formalization as verification with a faithfulness gate: FaithSieve admits formal evidence only after semantic alignment scoring, because provers otherwise verify "overly broad targets" or drifted statements. — [arXiv 2608.26310](https://arxiv.org/abs/2608.26310)
- DAG-first structure: ProofFlow's lemma DAG improved structural fidelity 4× over whole-proof formalization (0.545 vs 0.123). — [arXiv 2510.15981](https://arxiv.org/abs/2510.15981)
- Proof-style limitation: Herald skipped term-mode proofs as lacking a readable logical chain. — [Herald §3.1](https://arxiv.org/pdf/2410.10878)

### Inferences
- For a site that must trace each informal step to Lean, the natural output is structured: one record per `have`/lemma node (keyed by declaration name and source span) carrying its informal statement, its informal justification, and the names of the lemmas it cites; the readable proof is a *view* rendered from those records (summarized per dependency unit), not free text. The link survives because the summary is built from keyed parts.
- A cheap mechanical check exists that no paper reports: every lemma name and hypothesis the informal step mentions must appear in that step's tactic/term (or its premises). This catches the "reasoning not in the original proof" failure Hattori saw without an LLM judge.
- Term-mode or heavily automated steps (`simp`, `omega`, `decide`, `nlinarith`) have no human-meaningful step; an honest informalization labels them "routine computation (closed by `omega`)" rather than inventing reasoning.

### Gaps
- No evaluated system outputs informal steps keyed to source spans or declaration names as its published artifact.
- No study compares "from tactic state" vs "from proof term" vs "from source text only" on the same proofs with a faithfulness metric.

## 4. Cost and latency per proof

### Takeaway
No source reports dollar cost or latency for informalizing a proof. Published pipelines use small or mid models (GPT-4.1-mini; GPT-4o; DeepSeek Chat v2.5 as judge), which implies per-proof costs in cents for short proofs, but that is inference, not measurement.

### Cited Findings
- Hattori et al. used GPT-4.1-mini for all steps and summaries; one call per proof step plus one per summarization unit. No cost or timing reported. — [arXiv 2509.09726 §5.1](https://arxiv.org/pdf/2509.09726)
- Herald's validation used 128 parallel samples per statement for its formalization benchmark (formalization direction, not informalization). — [Herald §4.1](https://arxiv.org/pdf/2410.10878)
- Scale of the inputs: Gauss's Strong PNT is ~25,000 lines / 1,100+ declarations; the original Sendov formalization ~90,000 lines; Tao's re-formalization ~15,000 lines. — [math-inc/strongpnt](https://github.com/math-inc/strongpnt); [Tao, Aug 2026](https://terrytao.wordpress.com/2026/08/12/a-digestion-of-the-proof-of-sendovs-conjecture/)
- Human digestion cost (measured only anecdotally): Tao spent "several days (with heavy AI assistance)" on Sendov. — [Tao, Aug 2026](https://terrytao.wordpress.com/2026/08/12/a-digestion-of-the-proof-of-sendovs-conjecture/)

### Inferences
- Per-step informalization scales linearly with tactic count: a typical node proof of tens of steps is tens of short calls plus a few summary calls. For a network running this per merged proof, cost is dominated by extracting proof states (needs the Lean toolchain, i.e. the same build the gate does) rather than by the LLM.
- Very large agent proofs (10⁴–10⁵ lines) make line-by-line informalization both expensive and unreadable; the evidence (Sendov) points to digestion and re-formalization instead.

### Gaps
- No published tokens, dollars or seconds per proof for any informalization pipeline.

## 5. Tao and others on AI-produced Lean and human-readable write-ups (2025–2026)

### Takeaway
Tao's position through 2026: verification is now cheap, digestion is the bottleneck, AI exposition tends to dwell on trivialities and pass quickly over (or obscure) the novel steps, and a verified proof without a well-digested presentation is incomplete. His own practice (Sendov, Aug 2026) was human-led digestion with AI help, followed by re-formalization of the digested argument.

### Cited Findings
- AI writing "dwells at length on trivialities" while hurrying past genuinely novel steps, risking the loss of "natural friction" that helps readers learn (ICM 2026 lecture, 24 Jul 2026, as summarized on Tao's AI-views page). — [Tao, AI views page](https://teorth.github.io/tao-web/ai-views.html)
- "it is now easier to generate _long_ correct proofs than short ones" (21 Jun 2026). — [Tao, AI views page](https://teorth.github.io/tao-web/ai-views.html)
- Tao frames mathematics as generation → verification → digestion, with digestion "lagging dangerously behind" (Apr–Jun 2026). — [Tao, AI views page](https://teorth.github.io/tao-web/ai-views.html)
- ICM 2026: "if the authors cannot convincingly demonstrate that they can give a clear, expert-level talk on their results, that is correct and properly attributed, then the result should not be published". — [Tao, AI views page](https://teorth.github.io/tao-web/ai-views.html)
- Sendov: "the AI-generated proof was not human-digested to be in the form of a publication-ready preprint"; the digested proof turned out "remarkably elementary", which the 90k-line Lean did not make visible. — [Tao, Aug 2026](https://terrytao.wordpress.com/2026/08/12/a-digestion-of-the-proof-of-sendovs-conjecture/)
- Tao, quoted in this repo's earlier research: AI write-ups "dwell at length on trivialities while passing briefly through — or even actively obscuring — the most interesting and novel portions"; "blindly optimizing various metrics for 'digestibility' ... can make the final product worse"; a verified proof "remains only 2/3 of a solution until a proper, well-digested presentation". Secondary (not re-fetched this session). — [docs/research_math_and_ai_2026-09.html](../../research_math_and_ai_2026-09.html); likely primary: [Tao, "A severe misalignment of AI in mathematics", 11 Sep 2026](https://terrytao.wordpress.com/2026/09/11/a-severe-misalignment-of-ai-in-mathematics/)
- Tao's 2025 workflow note: when vibe-coding a Lean proof he learned to "first set up a human-readable proof of the lemma" (a lower-case blueprint) before formalizing; the vibe-coded proof ran to 1,125 lines, many on trivialities. (Search-result summary of his Mathstodon/blog posts.) — [Tao, Mathstodon](https://mathstodon.xyz/@tao/115493667607261044)
- Erdős #728: Tao's thread prefers a final write-up by humans (post titled "My preference would still be for the final writeu…"; full text could not be fetched). — [Tao, Mathstodon, Jan 2026](https://mathstodon.xyz/@tao/115855852706322322)
- Thomas Bloom (erdosproblems.com), via this repo's earlier note: reserves judgement "until I am confident that humans have read and vouched for the proof". Secondary. — [docs/research_math_and_ai_2026-09.html](../../research_math_and_ai_2026-09.html)

### Inferences
- For the network's use case, Tao's critique applies directly to faithful line-by-line informalization: it will be faithful *and* dwell on trivialities, because agent proofs spend most of their lines on routine steps. Faithfulness and digestibility are separate properties; per-step traceability secures the first, not the second.
- A defensible design is two layers: a mechanically generated, step-keyed informal rendering labelled as machine-generated (faithful, traceable, not digested), and a separate human-signed explainer that may restructure. This matches Sendov's sequence.

### Gaps
- Equational Theories Project (Tao et al., 2024–2025) commentary on readability of ATP-generated proofs was not fetched this session.
- Full text of Tao's January 2026 Mathstodon thread on Erdős #728 write-ups could not be retrieved (fetch returned only titles).
