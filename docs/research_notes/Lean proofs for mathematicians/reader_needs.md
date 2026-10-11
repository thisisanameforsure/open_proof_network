# Reader needs: what research mathematicians need to read, follow and trust a proof whose ground truth is a machine-checked formal proof (as of October 2026)

Scope note: notes compiled 2026-10-03. Every item is dated where the source gives a date. "Verified" below means
I read the primary text (PDF or page) myself; "summary" means the claim comes from a search or fetch summary and
was not checked against the full text.

## 1. Empirical and HCI evidence on how mathematicians read proofs (formal, structured, expandable)

### Takeaway
The best empirical model of what "understanding a proof" means is the seven-dimension Proof Comprehension Assessment
Model (Mejía-Ramos et al. 2012): three local dimensions (meaning of terms, justification of each claim, logical
structure) and four holistic ones (high-level ideas, general method, modular structure, application to examples).
Studies of research mathematicians show they read published proofs mostly for insight and method, not
line-by-line verification, often "modularly", and lean on the authority of who has checked it. There is no
controlled study I could find of research mathematicians reading Lean output or Lamport-style hierarchical
proofs; the evidence for expandable/hierarchical presentation is argument, practitioner experience (blueprints)
and one informal blog experiment (Gowers).

### Cited Findings
- **Proof Comprehension Assessment Model (2012).** Mejía-Ramos, Fuller, Weber, Rhoads and Samkoff built a
  seven-part model of proof comprehension from a literature review and semi-structured interviews with
  mathematicians: three "local" dimensions (meaning of terms and statements; justification of claims; logical
  structure / status of statements) and four "holistic" ones (higher-level ideas; general method; modular
  structure; application to examples). Only the originators have done rigorous test design from it (multiple-choice
  tests for three proofs in number theory and real analysis). — [Comparative judgement, proof summaries and proof comprehension (Educ. Stud. Math., 2020)](https://link.springer.com/article/10.1007/s10649-020-09984-x); [Rutgers record of the 2012 model paper](https://www.researchwithrutgers.com/en/publications/an-assessment-model-for-proof-comprehension-in-undergraduate-math/); [validated tests (RME 19(2), 2017)](https://www.tandfonline.com/doi/abs/10.1080/14794802.2017.1325776) (summary)
- **Proof summaries as a comprehension measure (2020).** Davies, Alcock and Jones used comparative judgement of
  students' written proof summaries as an alternative way to assess comprehension; i.e. "can you summarise the
  proof's idea" is itself treated as evidence of understanding. — [Educ. Stud. Math. 2020](https://link.springer.com/article/10.1007/s10649-020-09984-x) (summary)
- **Why and how mathematicians read proofs (2011).** Weber and Mejía-Ramos identify three strategies research
  mathematicians use: appeal to the authority of others who have read the proof, line-by-line reading, and
  *modular* reading; non-deductive reasoning plays a role in all three. — [Educ. Stud. Math. 76:329–344 (2011)](https://link.springer.com/article/10.1007/s10649-010-9292-z) (summary)
- **Follow-up survey.** Mathematicians report they commonly read published proofs to gain insight rather than to
  check correctness; they appeal to the reputation of author and journal, test steps on specific examples, and
  focus on the overarching ideas and methods. — [Mejía-Ramos & Weber, "Why and how mathematicians read proofs: further evidence from a survey study"](https://www.semanticscholar.org/paper/Why-and-how-mathematicians-read-proofs:-further-a-Mej%C3%ADa-Ramos-Weber/87fee429de61ccbd9aa4a4cbee499b013cfd25e7) (summary)
- **Five reading strategies mathematicians want (verified).** Weber and Mejía-Ramos: (1) try to prove the theorem
  before reading its proof; (2) compare assumptions and conclusion with the proof technique used; (3) break a
  longer proof into parts or sub-proofs; (4) compare the proof's approach with one's own; (5) use an example to
  understand a confusing inference. In their survey of 83 mathematicians and 175 majors, e.g. 88% of
  mathematicians vs 31% of majors chose strategy 1; 87% of mathematicians vs 26% of majors chose the
  approach-comparison item; 77% vs 43% for using examples. — [Weber & Mejía-Ramos, "Effective but underused strategies for proof comprehension", PME-NA proceedings (ERIC ED584498; year not printed in the extract)](https://files.eric.ed.gov/fulltext/ED584498.pdf)
- **Eye-tracking, experts vs novices (2012).** Inglis and Alcock recorded eye movements of undergraduates and
  research mathematicians validating purported proofs: mathematicians shift attention between lines more and
  attend to implicit warrants; undergraduates dwell on algebraic surface features. Experts agreed on arguments
  with clear reasoning errors but *disagreed* on arguments that were poorly expressed or had a "gap". — [JRME 43(4):358–390 (2012)](https://www.nctm.org/Publications/journal-for-research-in-mathematics-education/2012/Vol43/Issue4/Expert-and-Novice-Approaches-to-Reading-Mathematical-Proofs/); disputed in part by [Weber & Mejía-Ramos, "On mathematicians' proof skimming: a reply to Inglis and Alcock" (JRME 2013)](https://sites.math.rutgers.edu/~jpmejia/files/Weber%20&%20Mejia-Ramos%20(2013JRME).pdf) (summary)
- **Self-explanation training (2014).** A short booklet focusing readers on logical relationships within a proof
  improved comprehension (d = 0.95), increased the frequency of attention shifts around the proof, and a 15-minute
  version had a lasting effect. — [Hodds, Alcock & Inglis, JRME 45(1):62–101 (2014)](https://pureportal.coventry.ac.uk/en/publications/self-explanation-training-improves-proof-comprehension/) (summary)
- **Multimedia "e-proofs" eye-movement study (2017).** Studied resources designed to support learning from written
  proofs (animated, narrated highlighting of proof lines). — [Educ. Stud. Math. 2017](https://link.springer.com/article/10.1007/s10649-017-9754-7) (title only; findings not read)
- **Structured proofs, 1983.** Leron's "structural method" arranges a proof top-down in levels of short autonomous
  "modules", each embodying one major idea; the top level is short and free of technical detail, the bottom
  resembles a standard linear proof. — [Leron, "Structuring Mathematical Proofs", Amer. Math. Monthly, March 1983 (ERIC EJ277000)](https://eric.ed.gov/?id=EJ277000) (summary)
- **Lamport's structured proofs (2011/2012, verified).** Two principles: *structure* (the function of every
  assertion is explicit) and *naming* (every fact used is cited by name). "Proper structuring allows us to add as
  much detailed explanation as we like without obscuring the larger picture." With hypertext, readers "will first
  see the corollary with no proof", tap to see "just the five steps", and "can stop opening lower levels of the
  proof when satisfied that she understands why the statement is true." The structured version took ~40% more
  vertical space. How much detail "depends on the sophistication of the reader". Lamport explicitly separated
  "easier to read" from "more rigorous" because asking for both was "too high a barrier for most mathematicians". —
  [Lamport, "How to Write a 21st Century Proof", J. Fixed Point Theory Appl. (2012)](https://lamport.azurewebsites.net/pubs/proof.pdf)
- **Observation study of proof-assistant users (April 2025, verified header).** Contextual inquiry with 30
  Rocq/Lean users: proof writers iterate by reacting to feedback from the assistant; progress involves "challenging
  conversations" with it; they consult a wide array of external resources; and they are guided by design concerns
  beyond "getting to QED". Participants noted that term-mode golfing costs readability, and some aim to make lemma
  *statements* (not scripts) "readable and self-contained". — [Shi, Torczon, Goldstein, Pierce, Head, "QED in Context", PACMPL 9 OOPSLA1, Art. 92 (2025)](https://jwshii.github.io/OOPSLA25.pdf)
- **Adaptive proof explanation (older AI work).** Fiedler's P.rex (c. 1999–2001, Ωmega system) chose a degree of
  abstraction per proof step from a user model (ACT-R) of facts and rules the reader is assumed to know, and
  entered clarification dialogs to revise it; motivated by the observation that proof presenters "simply present
  proofs without motivating why the proof is done as it is done" and ignore the user. — [P.rex: An Interactive Proof Explainer](https://link.springer.com/chapter/10.1007/3-540-45744-5_33); [IJCAI 2001](https://mlanthology.org/ijcai/2001/fiedler2001ijcai-dialog/) (summary)

### Inferences
- A translation layer can be designed against the seven PCAM dimensions directly: each page should let a reader
  (a) look up every term (local: meaning), (b) see the justification of each step (local: justification),
  (c) see each step's logical status — assumption, claim, case, conclusion (local: structure), and holistically
  (d) state the key idea, (e) name the method, (f) see the modular decomposition, and (g) work an example.
- Mathematicians' reliance on "authority" in reading is exactly what a formal check can substitute for at the
  correctness level, freeing the page to concentrate on insight, method and modular structure; but statement
  fidelity remains an authority question (see §3).
- The Inglis–Alcock finding that experts disagree about *gaps* and poor expression (not about clear errors)
  suggests the useful role of the formal proof on a page is to resolve "is this a gap?" on demand by expanding.

### Gaps
- I found no controlled study of research mathematicians reading Lean proofs, Lean infoview output, Alectryon/Verso
  annotated proofs, or blueprint pages. Evidence there is testimony (Scholze, Tao, Avigad) not experiment.
- No empirical test of Lamport-style hierarchical proofs with research mathematicians found; Leron and Lamport are
  argument and practice. A claim in a fetch summary that Lamport says "one third of papers contain errors" does
  not appear in the 2011/2012 paper text I read (it may be from his 1995 Monthly paper); treat as unverified.
- The Weber–Mejía-Ramos strategies paper's year was not in the extracted text.

## 2. What mathematicians have said about reading formalized or AI-generated proofs

### Takeaway
The consistent message from 2021 to 2026: definitions and theorem *statements* in Lean are readable to
mathematicians, tactic proofs are not; formal verification settles truth but not understanding; and AI write-ups
currently get the polish right while burying the interesting idea, omitting literature and overview, and removing
the "friction" that signals where the hard part is. Community declarations in 2026 ask for human descriptions of
central arguments, disclosure of tools, and proactive attribution.

### Cited Findings
- **Scholze on reading Lean (5 June 2021, verified).** "The definitions and theorems are surprisingly readable,
  although I did not receive any training in Lean. But I cannot read the proofs at all — they are analogous to
  referring to theorems only via their LaTeX labels, together with a specification of the variables to which it
  gets applied; plus the names of some random proof finding routines. Still, I have the feeling that it should be
  possible to create a completely normal mathematical manuscript that is cross-linked with the Lean code that makes
  it possible to navigate the Lean code seamlessly." — [Xena: Half a year of the Liquid Tensor Experiment](https://xenaproject.wordpress.com/2021/06/05/half-a-year-of-the-liquid-tensor-experiment-amazing-developments/)
- **Scholze on what formalization taught him (same post, verified).** He had not understood why the argument
  worked; formalizing Gordan's lemma made him realise "the key thing happening is a reduction from a non-convex
  problem over the reals to a convex problem over the integers." Also: "Lean always gives you a clear formulation
  of the current goal" and Commelin "could … really only see one or two steps ahead"; the blueprint was written
  *after* each lemma was formalized, "now thoroughly digested". — [same](https://xenaproject.wordpress.com/2021/06/05/half-a-year-of-the-liquid-tensor-experiment-amazing-developments/)
- **A commenter on the same post (2021, verified)** diagnosed why: a tactic script "doesn't tell you about X, Y,
  and Z [the goals and hypotheses]. It only contains the word 'induction'", and asked for "a tool that takes a Lean
  proof and prints a human-readable version with assumptions and goals in each step". — [same, comments](https://xenaproject.wordpress.com/2021/06/05/half-a-year-of-the-liquid-tensor-experiment-amazing-developments/)
- **Tao, ICM 2026 public lecture (24 July 2026, verified from slides).** "Could we have a verified proof of a
  major result that no human understands enough to explain it?" AI exposition: "spelling, grammar, and formatting
  is close to flawless. However, the writing often dwells at length on trivialities, while passing very briefly
  through (or even obscuring) the most interesting and novel portions of the argument. AI-generated texts also often
  fail to note connections with prior literature, or provide high level overviews of the result." Over-polish: "A
  proof may end up being too slickly written — with both the routine and difficult parts of the argument being
  presented as equally easy to digest. In a human-written proof, the parts of the argument that the author found
  difficult will typically retain some natural friction that prompts the reader to slow down." Also: authors aid
  digestion "by describing their own insights and stories", but "current AI tools are quite opaque about their
  problem-solving process." Predicts "Many verified AI-generated proofs will await a readable writeup." Notes
  erdosproblems.com holds "dozens of AI-generated proof submissions … no human expert has yet volunteered to verify
  and vouch for them". Recommends "responsible disclosure of AI assistance." — [Tao, "Mathematics in the age of AI" slides](https://teorth.github.io/tao-web/slides/age-of-ai-icm-2026.pdf); essay version [arXiv:2608.16753 (17 Aug 2026)](https://arxiv.org/abs/2608.16753)
- **Leiden Declaration (2 June 2026, IMU-endorsed).** Proofs confer certainty "as well as imparting understanding
  of why their conclusions are true"; automated techniques "can produce plausible but unreliable (or even
  incorrect) arguments which are difficult to distinguish from correct mathematical proofs"; recommends standards
  that "might include requiring human descriptions of central arguments obtained by automated tools, insisting on
  formal verification when appropriate"; asks authors to disclose tools ("a 'Tool and computational resource
  disclosure' section"), give "precise and complete references to previous results", and make "proactive effort to
  find and credit the sources" given tools' attribution limits; responsibility "remains exclusively with the human
  authors". — [leidendeclaration.ai](https://leidendeclaration.ai); context [CACM blog](https://cacm.acm.org/blogcacm/the-leiden-declaration-mathematics-ai-and-making-our-values-explicit/)
- **Fields-medallist declaration (11 Sept 2026).** "Solving problems is only a tool and proxy for achieving the
  primary goal of conceptual understanding and insight"; AI solutions "announced in a rush, leaving no time for a
  proper writeup, the isolation of new methods and ideas"; without mathematicians to integrate them "AI-conceived
  ideas would never become fully alive"; warns "the crucial human transmission chain between mathematicians would
  be lost". — [mathandai.org](https://mathandai.org/) (summary of page). Signatory count conflicts: 25 per
  [Scientific American](https://www.scientificamerican.com/article/25-winners-of-maths-nobel-prize-decry-the-ai-invasion-of-their-discipline/) and [Tao on Mathstodon](https://mathstodon.xyz/@tao/117253629967855195); 27 per the fetch of mathandai.org (perhaps signatures added later).
- **Guest post on Tao's blog (23 Sept 2026, verified).** On OpenAI's forced Navier–Stokes blow-up proof
  (announced 8 Sept 2026, "formalized and verified in Lean"): "The formal verification supports its correctness,
  but mathematicians are still working to digest it." Quotes Rav: "theorems are the headlines, proofs are the
  inside story"; "A proof that is correct but incomprehensible … gives us the headline without the story." Quotes
  Gowers: "the inadequate AI-generated write-ups of proofs are likely a temporary annoyance." — [Tapio Schneider, "Headlines and inside stories"](https://terrytao.wordpress.com/2026/09/23/headlines-and-inside-stories-understanding-and-trust-in-ai-for-mathematics-science-and-engineering/)
- **Avigad, "Mathematics and the formal turn" (Bull. AMS 61(2), 2024; arXiv Nov 2023, verified).** "One needs to
  have confidence that the formal statement that has been verified is an adequate representation of the informal
  theorem we have in mind. When the statement of a theorem is elementary … that is generally not a big concern, but
  when the statement builds on complex machinery, a more careful audit is called for" (citing Commelin's and
  Topaz's LTE audit talks). On presentation he describes the Massot–Miller prototype (below) and concludes "the goal
  of formalization is not to replace mathematical exposition but, on the contrary, to enhance it." —
  [arXiv:2311.00007](https://arxiv.org/pdf/2311.00007); [Bull. AMS](https://www.ams.org/journals/bull/2024-61-02/S0273-0979-2024-01832-1/S0273-0979-2024-01832-1.pdf)
- **Alper (Bull. AMS 63(2), 2026; written Sept 2024).** Asks "how can you be certain that the statement of the
  theorem in Lean is equivalent to the statement in a paper or book?"; proposes that after formalization "authors
  can write a lengthy introduction with a high-level exposition of the proof emphasizing the key new insights",
  since the formal proof carries the details. — [Alper, "Embracing AI and formalization"](https://www.ams.org/journals/bull/2026-63-02/S0273-0979-2025-01879-0/viewer/) (summary)
- **A worked example of a human write-up of an AI Lean proof (Jan 2026, verified).** Sothanaphan's write-up of
  Aristotle's Lean proof of Erdős #728: the Lean proof "boosts confidence in correctness, [but] may not be readily
  digestible"; much of the text was drafted by ChatGPT but "everything has been manually checked up to roughly the
  level that the author himself would be confident in were he to write it himself"; a table maps each of the
  paper's 14 lemmas to the Lean declaration that proves it (some to Mathlib lemmas, some "proved inside" another
  lemma); it records the story including that the problem "as stated on the website was vague", the first AI
  proof resolved one reading, and community consensus then judged it partial; and it adds a literature
  comparison (Pomerance's similar extension). — [arXiv:2601.07421](https://arxiv.org/abs/2601.07421)
- **Human audit of AI proofs (Aug–Sept 2026).** An audit of OpenAI's ten announced results (1 Aug 2026) found no
  persisting substantive error in principal results, but one chapter needed major revision of "compressed analytic
  arguments", one had an apparent polarity error caused by a typeset overbar lost in PDF extraction, review depth
  varied and some dependencies stayed partly unchecked; concludes confidence requires "formal checking, human
  reconstruction, independent mathematical use, and a public record supporting correction." — [Sienicki & Sienicki, arXiv:2608.14673](https://arxiv.org/abs/2608.14673) (summary of abstract)
- **Correspondence problem (March 2026).** DeDeo and Duede argue a formal derivation justifies an informal proof
  only if it (1) *adequately represents* the theorem and (2) *tracks* the steps of the informal proof; actual
  formalization systems establish both "quasi-empirically". — [arXiv:2603.13680](https://arxiv.org/abs/2603.13680) (summary)
- **Opposition view (Aug 2026).** Weinreich makes "the case for total opposition to the use of artificial
  intelligence in mathematics". — [arXiv:2608.02859](https://arxiv.org/abs/2608.02859)

### Inferences
- A page whose ground truth is Lean can show statements and definitions nearly as-is (Scholze found them readable)
  but must never show a tactic script as "the proof" without the goals and hypotheses at each step.
- "Tracking" (DeDeo–Duede) is the property an informal translation must have to inherit trust from the formal
  proof: each prose step should be anchored to the formal step(s) it describes, as the Erdős #728 table does at
  lemma granularity.
- Tao's "friction" point argues against uniformly smooth prose: the page should mark which steps are routine
  (and can be collapsed) and which carry the idea, rather than presenting all as equally easy.
- The #728 story shows the risk the user asked about concretely: the informal *problem statement* was ambiguous,
  so a formally correct proof resolved a different reading. A summary that says "Erdős #728 solved" would have
  misstated the result.

### Gaps
- I did not find a 2025–2026 Buzzard, Massot, Commelin, Kontorovich or Gowers primary text specifically on what a
  readable account of a formal proof must contain; only Gowers's one-line remark via the guest post, and older
  LTE-era statements. The Commelin/Topaz LTE audit talks are cited by Avigad but not read here.
- The Weinreich paper's specific proposals were not read.

## 3. Human-style write-ups and automatic informalization (Ganesalingam–Gowers and successors)

### Takeaway
Ganesalingam and Gowers (2013) showed readers could not reliably tell their program's write-ups from students',
and recorded concrete reader preferences: restate the goal after each unfolding, use the field's preferred
definitions (open balls), and do not narrate how witnesses were found; they also argued output must be
*faithful* to the actual reasoning and proposed two output styles (proof vs discovery account). LLM informalization
of Lean (2025–26) is active research but evaluation by mathematicians is thin, and statement-level unfaithfulness
(a compiling statement that drops a hypothesis or changes a domain) is the documented failure.

### Cited Findings
- **Ganesalingam & Gowers (2013; J. Autom. Reasoning 2017), verified.** Program "presents solutions that are hard
  to distinguish from solutions that might be written by human mathematicians". Faithfulness requirement: "the
  steps that the program takes in order to discover the proofs … should be directly translated into human
  language", and for harder problems "we plan to have two styles of output. One will be a proof as a human might
  write it, and the other … an account … of the proof discovery process." — [arXiv:1309.4501](https://arxiv.org/abs/1309.4501)
- **Their blog experiment (March–April 2013), verified.** 15 write-ups (program, undergraduate, PhD student × 5
  problems) posted without disclosure; "Nobody expressed the slightest suspicion" that one was a program. Readers'
  three main criticisms of the program: it did not use open balls (the idiom of the field), it did not restate the
  new target after expanding definitions ("Several readers commented that they found this helpful"), and it spelled
  out how it found witnesses like min{η, θ} instead of declaring "Let δ = min{η, θ}". In a disclosed vote (300 to
  1000+ votes per problem) roughly half identified the program, many said they had no idea, and the authors note
  they could not tell whether experienced mathematicians were better at it. — [arXiv:1309.4501 §3](https://arxiv.org/pdf/1309.4501); [Gowers blog results post](http://gowers.wordpress.com/2013/04/14/answers-results-of-polls-and-a-brief-description-of-the-program/)
- **Massot–Miller prototype (c. 2023), verified via Avigad.** "Automatically translates a formal proof to one that
  is written in formulaic but otherwise ordinary English. In a browser, one can click on buttons interspersed
  through the text, to see all the objects and assumptions in play at that point in the proof. … one can click on a
  plus symbol next to any high-level inference, at which point, the display expands to include a justification of
  the inference … or click on a minus symbol to collapse the text again." — [Avigad, arXiv:2311.00007](https://arxiv.org/pdf/2311.00007)
- **Verbose Lean (Massot, ITP 2024).** Controlled-natural-language tactics so Lean proofs read like paper proofs;
  author reports it is not easier to learn than plain Lean but improves students' transfer to handwritten proofs. —
  [ITP 2024](https://drops.dagstuhl.de/entities/document/10.4230/LIPIcs.ITP.2024.27); [repo](https://github.com/PatrickMassot/verbose-lean4) (summary)
- **LLM informalization along proof structure (Sept 2025).** Hattori, Matsuzaki, Fujiwara verbalize each formal
  step and recursively summarise along the proof tree; evaluated against an undergraduate textbook's original
  proofs (INLG 2025). — [arXiv:2509.09726](https://arxiv.org/abs/2509.09726) (abstract only; metrics not read)
- **Statement unfaithfulness.** In statement autoformalization "models may generate declarations that compile while
  omitting a hypothesis, changing a domain, or weakening the conclusion, with the checker certifying the theorem the
  model wrote rather than the theorem the user meant." — [Beyond Compilation, arXiv:2606.31002 (2026)](https://arxiv.org/pdf/2606.31002) (search snippet)

### Inferences
- Concrete write-up rules from the only reader experiment found: (1) after unfolding a definition or splitting a
  goal, restate "We need to show that …"; (2) use the subfield's idiomatic definitions even when the formal library
  uses another; (3) declare witnesses ("Let δ = min{η, θ}") rather than narrate search; (4) keep a separate,
  optional "how it was found" account.
- An LLM-written informal layer over a Lean proof is "machine-written prose" and inherits no correctness from the
  Lean proof except where it is anchored step-by-step to it; the statement in words is the highest-risk element.

### Gaps
- No published evaluation found in which research mathematicians rated LLM informalizations of Lean proofs for
  followability or faithfulness; the Massot–Miller tool has no reported user study.

## 4. What "followable by a subfield expert" means operationally, and presentation patterns

### Takeaway
Operationally: idea and overview first; a hierarchical body whose top level is a few named steps; each fact cited
by its standard name (the name a textbook or the Stacks Project uses), not a Mathlib identifier; the subfield's
notation and idioms; goals restated at each step; routine steps visibly collapsible; and a dependency map with a
lemma-to-formal correspondence. Existing tools cover pieces: leanblueprint (dependency graph, LaTeX linked to Lean,
status colours), Verso/Alectryon (proof states inline in HTML), Mathlib's `@[stacks]`/`@[kerodon]` tags and
docstrings, the undergrad/100/1000+ theorem lists, and third-party explorers that map Mathlib to words.

### Cited Findings
- **Blueprints (Massot; LTE 2021, PFR Nov 2023).** Dependency graph of lemmas and definitions with status colours
  (green = fully formalized; blue = ready to formalize; green border = statement formalized); clicking a node shows
  the human-readable statement and LaTeX proof linked to the Lean declaration; lets work proceed on later stages
  without waiting. — [Tao, PFR blueprint tour (18 Nov 2023)](https://terrytao.wordpress.com/2023/11/18/formalizing-the-proof-of-pfr-in-lean4-using-blueprint-a-short-tour/); [leanblueprint](https://github.com/PatrickMassot/leanblueprint) (summary). The LTE blueprint was "a guide comprehensible to mathematicians with no Lean training". — [Xena 2021](https://xenaproject.wordpress.com/2021/06/05/half-a-year-of-the-liquid-tensor-experiment-amazing-developments/)
- **Proof states in documents.** Verso generates HTML in which "tactic proofs are annotated with their proof
  states, so the proof can be understood without having to open the file in a full Lean environment", UI inspired
  by Alectryon; LeanInk (Alectryon's Lean 4 bridge) is archived (last push July 2024, Lean v4.6.0-rc1). —
  [Verso](https://github.com/leanprover/verso); [Alectryon](https://github.com/cpitclaudel/alectryon) (summary)
- **Hierarchical/expandable detail.** Leron (1983) levels of modules; Lamport (2012) numbered steps with
  hypertext expansion and citation of every used fact by name; Massot–Miller plus/minus expansion and
  "objects and assumptions in play" buttons; Fiedler's P.rex per-step abstraction from a model of what the reader
  knows. — see §1 and §3 sources.
- **Naming: Mathlib vs textbook.** Mathlib lemma names are mechanical: names of the declarations involved in
  syntax-tree order, with `of` separating hypotheses (`C_of_A_of_B`). — [Mathlib naming conventions](https://leanprover-community.github.io/contribute/naming.html). Bridges that exist: `@[stacks]`/`@[kerodon]`
  attributes linking declarations to Stacks Project/Kerodon tags (with guidance that tagged lemmas "should probably
  have docstrings saying what they do in a way which a mathematician would understand") — [Mathlib.Tactic.StacksAttribute](https://leanprover-community.github.io/mathlib4_docs/Mathlib/Tactic/StacksAttribute.html), [external-tags](https://github.com/leanprover-community/external-tags);
  the Undergrad list (from the French curriculum) and Mathlib overview — [undergrad](https://leanprover-community.github.io/undergrad.html), [overview](https://leanprover-community.github.io/mathlib-overview.html);
  Mathlib Explorer, "for people who know mathematics but not Lean": each theorem shown in words with rendered
  math, then in Lean "with every name explained on hover", a "proof map, which unfolds step by step, routine steps
  counted apart", and links to Wikipedia, Stacks, Kerodon and cited books — [LeanTrustBuilders/mathlib-explorer README](https://github.com/LeanTrustBuilders/mathlib-explorer) (verified README; site not inspected).
- **Lemma-level correspondence table** as in the Erdős #728 write-up (paper lemma → Lean declaration, noting which
  are Mathlib lemmas and which are inlined). — [arXiv:2601.07421](https://arxiv.org/abs/2601.07421)
- **Overview and literature.** Tao: AI texts "fail to note connections with prior literature, or provide high
  level overviews"; Leiden asks for "precise and complete references to previous results"; Alper wants a
  "high-level exposition … emphasizing the key new insights". — sources in §2.

### Inferences (suggested requirements for a translation layer)
- R-a **Statement first, in two forms**: the informal statement in the subfield's notation and the Lean statement
  (readable per Scholze), with every definition it depends on one click away; flag any divergence or open
  fidelity question prominently.
- R-b **Idea paragraph and method name** before any steps (PCAM holistic dimensions; Tao; Alper).
- R-c **Top level of 3–7 named steps** (Lamport/Leron), each a claim whose status is explicit (assumption, claim,
  case split, conclusion), each expandable to sub-steps down to the formal proof state.
- R-d **Restate the goal** after every unfolding/split; declare witnesses, do not narrate search (Ganesalingam–Gowers).
- R-e **Cite standard results by their standard names** (e.g. "Kummer's theorem", "Mean Value Theorem", Stacks
  tag), with the Mathlib identifier as secondary hover text; source the mapping from `@[stacks]`, docstrings and
  curated lists rather than from an LLM guess.
- R-f **Mark routine vs essential steps** so friction survives (Tao); collapse routine ones by default.
- R-g **Dependency graph + correspondence table** (blueprint; #728), every informal step linked to the formal
  declaration(s) it tracks (DeDeo–Duede "tracking").
- R-h **Optional discovery account**, kept separate from the proof (Ganesalingam–Gowers two styles; Tao on
  insight stories), and a literature/attribution section (Leiden).
- R-i **Example hooks**: where possible, a concrete instance for confusing inferences (strategy 5; PCAM
  "application to examples").

### Gaps
- No source gives a validated level-of-detail rule for "subfield expert" beyond Lamport's "depends on the
  sophistication of the reader" and P.rex-style user models; the right default depth is untested.
- No comprehensive Mathlib-name → textbook-name dataset was found beyond Stacks/Kerodon tags, curated lists, and
  docstrings; coverage of research-level analytic number theory/combinatorics names is unknown.

## 5. Trust signals and accessibility

### Takeaway
The sources converge on separating three things a reader must not confuse: (1) what the kernel checked (the formal
statement and proof), (2) whether the formal statement is the intended theorem (a human audit question), and
(3) prose that a machine or person wrote about it (unverified). Declarations ask for disclosure of tool use and
human responsibility. For accessibility, MathML (with MathJax 4 speech/explorer or MathCAT) is the current route
to screen-reader and braille output; arXiv's HTML work (May 2026) adds MathML 4 intent annotations.

### Cited Findings
- Formal verification settles truth only relative to the formal statement; statement adequacy needs "a more
  careful audit" when the statement uses complex machinery — [Avigad 2024](https://arxiv.org/pdf/2311.00007); Alper asks the same question — [Bull. AMS 2026](https://www.ams.org/journals/bull/2026-63-02/S0273-0979-2025-01879-0/viewer/).
- Blueprint status colours are an established, mathematician-facing visual convention for formal status per node —
  [Tao 2023](https://terrytao.wordpress.com/2023/11/18/formalizing-the-proof-of-pfr-in-lean4-using-blueprint-a-short-tour/).
- Leiden: disclose tools in a dedicated section; human authors bear responsibility for correctness *and* adequacy
  of arguments and citations — [leidendeclaration.ai](https://leidendeclaration.ai). Tao: "Normalize the
  responsible disclosure of AI assistance" (his own slides footnote which parts were AI-assisted) — [ICM 2026 slides](https://teorth.github.io/tao-web/slides/age-of-ai-icm-2026.pdf).
- The #728 write-up's disclosure pattern: states a large fraction was drafted by ChatGPT, states the level of manual
  checking, links the LLM conversation, and maps lemmas to Lean — [arXiv:2601.07421](https://arxiv.org/abs/2601.07421).
- Audit lesson: an error introduced by format conversion (lost overbar in PDF extraction flipped a polarity) —
  rendering is part of the trust chain — [arXiv:2608.14673](https://arxiv.org/abs/2608.14673) (summary).
- Accessibility: MathML stores equations as structured text that screen readers can navigate; MathJax 4 provides
  speech via its a11y/explorer and a11y/speech components — [MathJax 4 accessibility docs](https://docs.mathjax.org/en/v4.1/basic/accessibility.html);
  MathCAT produces speech and braille (Nemeth, UEB Technical) from MathML and supports navigation — [mtm.se recommendations, spring 2025 tests](https://www.mtm.se/en/recommendations-for-stem-users/) (summary: NVDA + MathCAT recommended in 2025);
  arXiv HTML papers: ~75% error-free conversion, "initial MathML 4 Intent annotations for accessible speech
  output" — [Ginev et al., arXiv:2605.16562 (15 May 2026)](https://arxiv.org/abs/2605.16562) (summary).

### Inferences
- Each block on a page should carry one of a small set of provenance labels, visible as text not colour alone:
  *kernel-checked* (formal statement/proof, with the checking commit), *human-audited statement* (who, when),
  *machine-written prose, unverified* (model named), *human-written/edited prose* (who). Anchored prose
  ("this step = these Lean lines") should say so; unanchored prose should not borrow the checkmark.
- Render math as MathML (or KaTeX/MathJax output that emits MathML) so screen readers work; expandable sections
  need real `<details>`/ARIA semantics and keyboard access; Lean code and goal states must remain text (not images),
  wrap or scroll on phone widths, and have Unicode symbols readable by assistive tech.
- Verify that the informal statement shown is generated from or checked against the formal one; conversions are an
  error source (the overbar case).

### Gaps
- No usability study found of provenance labelling on mathematical pages, nor of screen-reader access to Lean
  infoview/goal states or Unicode-heavy Lean source specifically.
- I did not verify current KaTeX MathML output quality for screen readers.
