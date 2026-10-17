---
label: "Left projection given the swapped conjunction"
supersedes: null
drafted_with: Claude Fable 5.1 (claude-fable-5-1)
licence: CC-BY-4.0
---
$$\forall\, p\,q:\operatorname{Prop},\quad p\wedge q\ \Rightarrow\ q\wedge p\ \Rightarrow\ q\wedge p\ \Rightarrow\ p$$

For any two propositions $p$ and $q$: if $p\wedge q$ holds, and $q\wedge p$ holds (the earlier hole's claim, inherited as a hypothesis), and $q\wedge p$ holds again, then $p$ holds. The two copies of $q\wedge p$ are separate hypotheses as written, and $p$ already follows from the first hypothesis alone.
