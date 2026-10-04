# Lean-native tools that present Lean 4 proofs to mathematicians who do not read Lean (state as of 2026-10-03)

Method note: repository facts (last push, licence, archived flag, stars) were read from the GitHub REST API on 2026-10-03 (`gh api repos/<owner>/<name>`); CDN findings come from grepping shallow clones of each repo taken the same day. Those are cited to the repo URL. "Last push" means the date of the most recent push to any branch, not a release.

## 1. Patrick Massot's work: leanblueprint, Lean Verbose, and the "informalization" of Lean proofs (with Kyle Miller)

### Takeaway
Massot has three separate strands. **leanblueprint** (mature, widely used, slowing down) links a *hand-written* LaTeX document to Lean declaration names. **Lean Verbose** (active) is controlled-natural-language tactics, so it only helps with Lean written in its own style. **Informalization** (Massot and Miller) is the only one that turns ordinary Lean tactic proofs into expandable English automatically. It exists as a static demo page from February 2023 and a paper listed as "in preparation", with no public repository found. None of the three takes arbitrary agent-written Lean and gives prose without either hand annotation or Verbose-style source.

### Cited Findings
**leanblueprint (plasTeX plugin)**
- It is a plasTeX plugin for writing "blueprints" of Lean 4 projects, the concept from Tao's blog post. Macros: `\lean{}` (Lean declaration names), `\leanok` (fully formalized), `\uses{}` (dependencies, with statement uses kept apart from proof uses), plus `\notready`, `\mathlibok`, `\discussion` (GitHub issue), `\proves`. — [leanblueprint README](https://github.com/PatrickMassot/leanblueprint)
- Dependency-graph node states: `stated` (green), `can_state` (blue), `not_ready` (orange), `proved` (light green), `can_prove` (light blue), `defined`, `fully_proved` (dark green), `mathlib` (dark green). — [leanblueprint README](https://github.com/PatrickMassot/leanblueprint)
- The link to Lean is **by name only**. `checkdecls` "requires a compiled Lean project" and checks that every Lean name in the blueprint exists in the project or a dependency such as Mathlib. Formalization status comes from the author's hand-placed `\leanok`, not from inspecting the Lean code. — [leanblueprint README](https://github.com/PatrickMassot/leanblueprint)
- More than 40 projects use it, from sphere eversion to FLT. — [leanblueprint README](https://github.com/PatrickMassot/leanblueprint)
- Licence Apache-2.0. Last push 2025-12-23 (commit "Bump version number"). 380 stars, not archived. Its graph plugin `plastexdepgraph` was last pushed 2025-02-27. — [GitHub API: PatrickMassot/leanblueprint](https://github.com/PatrickMassot/leanblueprint); [PatrickMassot/plastexdepgraph](https://github.com/PatrickMassot/plastexdepgraph)
- **External resources:**
  - The graph plugin vendors its JavaScript (`d3.min.js`, `d3-graphviz.js`, `hpcc.min.js`, `graphvizlib.wasm`) under `plastexdepgraph/static`.
  - The graph template loads MathJax from `config.html5['mathjax-url']`. plasTeX 3.1 defaults that to `https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-chtml.js`, but it can be overridden with `--mathjax-url`, so MathJax can be vendored.
  - The Jekyll home-page template hard-codes `https://cdn.mathjax.org/mathjax/latest/MathJax.js`, which is the retired legacy CDN.
  — [plastexdepgraph repo](https://github.com/PatrickMassot/plastexdepgraph); [leanblueprint jekyll_templates/_include/mathjax.html](https://github.com/PatrickMassot/leanblueprint); [plasTeX on PyPI, Renderers/HTML5/Config.py](https://pypi.org/project/plasTeX/)

**Lean Verbose (verbose-lean4)**
- These are tactics and commands that let a proof be written in "controlled natural language" resembling a paper proof, in English and French. They are for teaching, not developer efficiency. The library has to be imported, and it **only applies to code written in its style**; it does not render arbitrary Lean. It includes a help tactic and a point-and-click widget. — [verbose-lean4 repo](https://github.com/PatrickMassot/verbose-lean4)
- ITP 2024 paper: students write proofs "that are easy to transfer to paper because they look like natural language", and teachers can customise the experience. The abstract mentions no export to informal text. — [Massot, Teaching Mathematics Using Lean and Controlled Natural Language, ITP 2024](https://drops.dagstuhl.de/entities/document/10.4230/LIPIcs.ITP.2024.27)
- Apache-2.0. Last push 2026-07-23. 158 stars. — [GitHub API: verbose-lean4](https://github.com/PatrickMassot/verbose-lean4)

**Informalization ("Mechanic informalization of Lean to English", Massot and Miller)**
- Commelin's PAT 2023 slides list "Massot's lean-verbose and informalization" and link `tinyurl.com/LeanIpam` as "Mechanic informalization of Lean to English by Patrick Massot and Kyle Miller". — [Commelin, Lean and Education, PAT 2023](https://pat2023.icube.unistra.fr/slides/slides-pat2023-commelin-talk1.pdf)
- That short link resolves to a demo page, `.../~patrick.massot/Examples/ContinuousFrom.html`, served with `Last-Modified: 15 Feb 2023`. The page contains:
  - a `declData` JSON for one lemma (`continuous_of_dense`), with the English statement "Let X be a topological space and let Y be a regular topological space. Let A be a dense subset of X. … Then f is continuous."
  - a tree of `Explanation.*` nodes: `withRefinement` (expandable detail, 45 instances), `withToolTip` (76), `goalState` (23 `GoalInfo` blocks that render the goal and hypotheses in words, e.g. "is a regular topological space"), `computation`, `enumList`.
  - **only local assets**: jquery-3.6.3, mithril, a local MathJax `tex-svg.js`, popper `core@2`, `tippy.js@6`, `split.min.js`, `script.js`, `style.css`.
  — [ContinuousFrom demo](https://www.imo.universite-paris-saclay.fr/~patrick.massot/Examples/ContinuousFrom.html) (fetched and inspected 2026-10-03)
- Terence Tao (Mathstodon, Feb 2023): Massot gave a demo of a tool that "automatically convert[s] a Lean proof into a web page providing an interactive human readable version of the proof". This wording is from the search-result summary; the post body would not render through the fetch. — [Tao on Mathstodon](https://mathstodon.xyz/@tao/109870724335427662)
- Kyle Miller's CV lists "Miller and Massot, *InformalLean: Natural structured proofs from formalized mathematics*" under **"In preparation"**. His talks "Informalizing formalized mathematics using the Lean theorem prover" were given in Apr 2023 (Freiburg algebra seminar; Languages, Systems, and Data Seminar) and Sep 2023 (EuroProofNet Workshop on Libraries of Formal Proofs and Natural Mathematical Language). The CV also lists him as co-PI on NSF DMS-2523479 (2025–2028, "AIMing: Automated Theorem Proving for Advancing Mathematics"). — [Kyle Miller CV](https://kmill.github.io/cv/cv.pdf)

### Inferences
- The informalization design (a static page carrying an explanation tree with expandable refinements, goal states rendered as English, and vendored JS) is the closest existing match to "an expandable informal proof on a static site with no CDN". The demo's data model (`Explanation.withRefinement`, `GoalInfo` with `singularType`/`pluralType`) is a concrete schema worth copying.
- Its English came from per-concept phrasing data (e.g. "is a regular topological space" and its plural), which looks like hand-curated templates per Mathlib notion. If that is right, arbitrary agent-written Lean over Mathlib concepts with no templates would fall back to less readable output. This is inferred from the data shape, not stated by the authors.
- leanblueprint status is author-asserted (`\leanok`), so on a network where agents write the Lean it is weaker than a status computed from the code. Verso Blueprint (§2) and LeanArchitect compute it instead.

### Gaps
- No public repository, preprint or Zulip thread for InformalLean / informalization was found. `gh search repos informal --owner PatrickMassot` and `--owner kmill` both returned nothing. Whether it was ported to current Lean 4 / Mathlib, its licence, and whether it needs hand annotations are all unknown.
- Whether the "ContinuousFrom" page was generated from Lean 3 or Lean 4 is not stated on the page. The 2023 date and the JSON shape fit early Lean 4 but this is unconfirmed.
- No statement from Massot was found on whether leanblueprint is being superseded by Verso Blueprint.

## 2. Verso, Verso Blueprint, SubVerso, doc-gen4, LeanInk/Alectryon, Paperproof, ProofWidgets, game server, infoview

### Takeaway
The Lean FRO's own stack is consolidating on **Verso**, with **SubVerso** providing highlighting, hovers and per-tactic proof states as JSON across Lean versions and **Verso Blueprint** providing dependency graphs with status computed from the code. Its FRO roadmap (Sep 2026 to Feb 2027) puts hardening these for mathematicians on the agenda. All of these show Lean (with goals and hovers), not English. LeanInk is archived. Alectryon still works for Rocq but needs the archived LeanInk for Lean 4. Paperproof is a VS Code panel with no documented static export. **Every Lean-FRO HTML generator still references jsdelivr/cdnjs in at least one template**, so a CDN-free site has to vendor and patch.

### Cited Findings
**Verso**
- Verso is the Lean FRO's documentation authoring tool. Genres include manual (used for the Lean reference), blog/website and textbook, and users can define their own. Code highlighting uses Lean's own parser, with hovers showing types, go-to-definition links and "rendered intermediate proof states in tactic proofs". It is inspired by Alectryon. Output is static HTML. — [leanprover/verso](https://github.com/leanprover/verso)
- Apache-2.0, last push 2026-10-02, release tags track Lean (e.g. v4.29.0), and the main branch is on `leanprover/lean4:v4.35.0-rc3`. — [GitHub API + clone: leanprover/verso](https://github.com/leanprover/verso)
- KaTeX, marked, popper, tippy, elasticlunr and axe-core are vendored under `vendored-js/`. But the manual genre's HTML template (`VersoManual/Html.lean`) loads `marked@11.1.1` from cdn.jsdelivr.net, and the blog genre template (`VersoBlog/Template.lean`) loads KaTeX 0.16.9 CSS/JS and marked from cdn.jsdelivr.net (with SRI hashes). — [verso source](https://github.com/leanprover/verso)
- FRO Year 4 Part 1 roadmap (September 2026 to February 2027): "Verso produces PDFs and interactive web pages from a single literate source". Verso Blueprints adds dependency-graph project views. The deliverable is "hardening Verso, Blueprints, and Games for reliability, performance, and everyday usability", smoother onboarding for mathematicians and educators, and a zero-install "Workbench" in beta. — [Lean FRO Year 4 Part 1 Roadmap](https://lean-lang.org/fro/roadmap/y4-1/)

**Verso Blueprint (successor-in-practice to leanblueprint)**
- A Lean package for writing blueprints in Verso. It combines informal exposition, links to local Lean code or existing declarations, and optional external TeX/Markdown attachments "to help port existing documents". It tracks progress automatically "by analyzing the associated Lean code and declarations, including incomplete declarations such as `sorry`". It renders dependency graphs and progress summaries, and produces "HTML output with previews, navigation, and exported metadata" under `_out/site/html-multi/`, plus optional PDF via LuaLaTeX. — [leanprover/verso-blueprint README](https://github.com/leanprover/verso-blueprint)
- Linking syntax:
  - inline labeled `lean "label"` code blocks
  - `@[blueprint "label"]` on a theorem, with `(autoDeps := true)` and `proofUses`
  - `(lean := "Nat.add_assoc")` for an existing declaration

  There is an agent-facing skill (`skills/verso-blueprint/`, `lake exe vbp query work-queue`). The widget surface is marked experimental. "the sole maintained release line" is v4.34.0. — [verso-blueprint README](https://github.com/leanprover/verso-blueprint)
- Reference blueprints built as release validation: Noperthedron, FLT, Carleson and Sphere Packing. — [verso-blueprint README](https://github.com/leanprover/verso-blueprint)
- No LICENSE file at the top level, and the GitHub API reports licence "none". Last push 2026-09-30. Toolchain `v4.34.1`. 34 stars. — [GitHub API + clone: verso-blueprint](https://github.com/leanprover/verso-blueprint)
- **External resources:** `Commands/graph.mjs` defaults `d3@7.9.0` and `d3-graphviz@5.6.0` to cdn.jsdelivr.net (`defaultGraphRuntimeLibraryUrls`), overridable via an `options.libraries` object. The widget loads d3, d3-graphviz and KaTeX ESM from jsdelivr. HTML maths uses Verso's vendored KaTeX. — [verso-blueprint source](https://github.com/leanprover/verso-blueprint)
- Talks on it: Gallego Arias (Lean FRO) at MadLean, Madrid, 2026-05-27, and at the ForMath seminar, IRIF, 2026-09-21. — [madlean slides repo](https://github.com/ejgallego/2026-05-27-madlean-verso-blueprint-slides); [formath slides repo](https://github.com/ejgallego/2026-09-21-formath-verso-blueprint-slides)

**LeanArchitect (blueprint from Lean source)**
- `@[blueprint]` attributes on Lean declarations generate leanblueprint-compatible LaTeX and JSON. Dependencies are inferred from the constants used in statements and proofs (overridable with `uses`/`proofUses`). Hand-written LaTeX nodes can be mixed in, and there are conversion tools for existing projects. Apache-2.0, last push 2026-09-25, 87 stars. — [hanwenzhu/LeanArchitect](https://github.com/hanwenzhu/LeanArchitect); [GitHub API](https://github.com/hanwenzhu/LeanArchitect)

**SubVerso**
- A support library that extracts highlighting, hover data, the names a command defines, and proof states (for anchor-marked regions) from Lean modules as JSON, so that Verso can document code from several Lean versions. CI checks it "on every Lean release since 4.0.0". Apache-2.0, last push 2026-10-02. — [leanprover/subverso](https://github.com/leanprover/subverso)

**doc-gen4**
- Generates static HTML API docs for a Lean project. Source links go to GitHub by default (`DOCGEN_SRC`: github, file or vscode). Docstrings are Markdown with maths. Equations for definitions are on by default. It requires the code to compile and tolerates `sorry`. Apache-2.0, last push 2026-09-30, toolchain `v4.35.0-rc3`. — [leanprover/doc-gen4](https://github.com/leanprover/doc-gen4)
- **External resources:** `Output/Template.lean` loads `cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js` and a cdnjs polyfill, and `static/style.css` imports JuliaMono and Lato from cdnjs. — [doc-gen4 source](https://github.com/leanprover/doc-gen4)

**LeanInk + Alectryon**
- LeanInk was a CLI helper that produced annotated output from Lean 4 for Alectryon (it needed a fork of Alectryon). **Archived (read-only) since August 2024**; last push 2024-07-18; Apache-2.0. No successor is named in the repo. — [leanprover/LeanInk](https://github.com/leanprover/LeanInk); [GitHub API](https://github.com/leanprover/LeanInk)
- Alectryon interleaves prose with recorded goals and responses in static HTML, where the reader reveals goals line by line. Rocq is the primary target; Lean 4 goes through LeanInk and Lean 3 support is preliminary. MIT, last push 2026-06-02. — [cpitclaudel/alectryon](https://github.com/cpitclaudel/alectryon)

**Paperproof**
- Renders Lean 4 tactic proofs (`by ...`) as a proof tree: hypotheses as green nodes, goals as red, tactics as dashed nodes, "resembling pen-and-paper". It works on ordinary tactic proofs (`apply`, `rw`, `intro`, `cases`, `induction`, `have`, `use`, `by_contra`, …), including Mathlib examples. It ships as a **VS Code extension** with a panel. The README mentions LaTeX, Snapshots and Single-Tactic Mode in a video but documents no static HTML export. MIT, last push 2026-09-06, 553 stars. Its web assets pull Google Fonts. — [Paper-Proof/paperproof](https://github.com/Paper-Proof/paperproof); [GitHub API](https://github.com/Paper-Proof/paperproof)

**ProofWidgets4, lean4game**
- ProofWidgets4 (the library for user widgets in the infoview): Apache-2.0, last push 2026-09-28, 226 stars. — [leanprover-community/ProofWidgets4](https://github.com/leanprover-community/ProofWidgets4) (GitHub API)
- lean4game, the game server: GPL-3.0, last push 2026-10-02, 563 stars. It was "revamped into a generic game server in Lean 4 by Patrick Massot and later Jon Eugster and Alexander Bentkamp" (live at adam.math.hhu.de). — [lean4game](https://github.com/leanprover-community/lean4game) (GitHub API); [Commelin PAT 2023 slides](https://pat2023.icube.unistra.fr/slides/slides-pat2023-commelin-talk1.pdf)

### Inferences
- For a static, CDN-free page that shows *the Lean with goal states*, SubVerso JSON plus your own renderer, or Verso's code-block HTML with vendored assets patched in, is the viable current path. LeanInk/Alectryon is a dead end for Lean 4.
- Paperproof's tree is the most mathematician-friendly visual of an arbitrary tactic proof, but it needs a live Lean server in VS Code. Putting it on a static page would mean extracting its data offline, which nothing documents.
- ProofWidgets and the game server depend on a running Lean server (the game server is GPL-3.0), so neither fits a static-site generator.
- Verso Blueprint's licence is unclear because no licence file was found. Check before vendoring any of its code.

### Gaps
- Whether Verso's tactic-state rendering works on an arbitrary external file without anchors, or only on code elaborated inside the Verso document, was not confirmed.
- Whether Verso Blueprint can import a leanblueprint `.tex` source directly: the README mentions only "optional external TeX ... attachments to help port existing documents".
- The infoview's own packaging (`@leanprover/infoview`) was not researched.
- No documented static export was found for Paperproof (the `paperproof.xyz` directory in the repo was not inspected).

## 3. Blueprint dependency graphs in FLT, PFR, Carleson, Equational Theories, sphere packing

### Takeaway
Through 2025 these projects linked a LaTeX statement to Lean by putting declaration names in `\lean{}`, with status from hand-placed `\leanok`/`\mathlibok`, name existence checked by `checkdecls`, and the graph coloured by those flags. In 2026 FLT, Carleson, Sphere Packing and Noperthedron are built as Verso Blueprint reference projects, where status is derived from the code itself (including `sorry`).

### Cited Findings
- leanblueprint mechanics: `\lean`, `\leanok`, `\uses`, `checkdecls`, and the colour states above. — [leanblueprint README](https://github.com/PatrickMassot/leanblueprint)
- Tao's PFR tour describes using leanblueprint for PFR. — [Tao, Formalizing the proof of PFR in Lean4 using Blueprint: a short tour](https://terrytao.wordpress.com/2023/11/18/formalizing-the-proof-of-pfr-in-lean4-using-blueprint-a-short-tour/)
- Verso Blueprint publishes Noperthedron, FLT, Carleson and Sphere Packing as reference blueprints, selected by `branch-policy.json` and `tests/harness/projects.json`. — [verso-blueprint README](https://github.com/leanprover/verso-blueprint)

### Inferences
- In both systems the prose is human-written, and the link is a declaration name or label, not a mapping from proof steps to sentences. Neither generates mathematics from Lean.

### Gaps
- The Equational Theories project's blueprint and its specific tooling were not checked. Nor was whether FLT/Carleson have fully moved off leanblueprint or publish both versions.

## 4. Tools producing tactic-state traces / goal-by-goal displays for a static page

### Takeaway
SubVerso (JSON proof states, maintained, Apache-2.0) and Verso's HTML are the current options. Alectryon+LeanInk is archived for Lean 4. The Massot/Miller demo shows the target output form (goals in English, expandable) but no released tool. Paperproof's trees are editor-only.

### Cited Findings
- SubVerso extracts proof states and highlighting as JSON across Lean versions. — [leanprover/subverso](https://github.com/leanprover/subverso)
- Verso HTML includes "rendered intermediate proof states in tactic proofs". — [leanprover/verso](https://github.com/leanprover/verso)
- Alectryon's static goal display: Rocq primary, Lean 4 only via the archived LeanInk. — [alectryon](https://github.com/cpitclaudel/alectryon); [LeanInk](https://github.com/leanprover/LeanInk)
- The informalization demo carries 23 goal states rendered as English hypothesis lists inside a static page. — [ContinuousFrom demo](https://www.imo.universite-paris-saclay.fr/~patrick.massot/Examples/ContinuousFrom.html)

### Inferences
- A pipeline that fits the constraints: extract the goals with SubVerso, or with a small Lean metaprogram over `InfoTree`s as SubVerso does, at gate time. Then render them with the site's own vendored KaTeX, using Massot's `Explanation`/`GoalInfo` shape as the display model. This is a design inference, not an existing tool.

### Gaps
- No maintained tool was found that produces goal-by-goal *English* (as opposed to Lean-syntax goals) for arbitrary Lean 4.

## 5. Analogues in other provers

### Takeaway
Naproche/ForTheL (Isabelle-integrated, active, GPL-3.0) is the strongest example of "the source *is* readable mathematics", and it has reached research-level material (perfectoid rings, ITP 2025). Lamport's hierarchical numbered proofs offer a presentation discipline that maps naturally onto expandable Lean `have` trees. Isar and Mizar were not researched in primary sources in this pass.

### Cited Findings
- Naproche checks natural-language input written in the controlled language ForTheL, and was integrated into the Isabelle Prover IDE in 2018, checking with E, Vampire and other ATPs. — [The Isabelle/Naproche Natural Language Proof Assistant (CADE 2021)](https://link.springer.com/chapter/10.1007/978-3-030-79876-5_36); [Naproche publications](https://naproche.github.io/publications.html)
- ITP 2025: "A Natural Language Formalization of Perfectoid Rings in Naproche". — [LIPIcs ITP 2025.6](https://drops.dagstuhl.de/storage/00lipics/lipics-vol352-itp2025/LIPIcs.ITP.2025.6/LIPIcs.ITP.2025.6.pdf)
- naproche/naproche: GPL-3.0, last push 2026-09-30. — [naproche/naproche](https://github.com/naproche/naproche) (GitHub API)
- Lamport's method rests on structure and naming: hierarchical numbering of steps, with every fact used named, and a scheme that prevents references to sub-proofs proved under different assumptions. It was inspired by TLA+ proofs. — [Lamport, How to Write a 21st Century Proof (2011)](https://lamport.azurewebsites.net/pubs/proof.pdf)

### Inferences
- Lamport's levels correspond to Massot's `withRefinement` nodes: each `have` or subgoal becomes a numbered step whose proof expands. That gives an informal structure that can be generated mechanically from any tactic proof without understanding the mathematics.

### Gaps
- Isabelle/Isar's document preparation (static HTML / PDF of readable structured proofs), Mizar's readable language and its HTML presentation, and Rocq's newer documentation tooling were not checked against primary sources in this pass.
