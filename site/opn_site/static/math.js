// Math in record prose (F04-T13): a curated record's informal statement may carry TeX between
// dollar signs, copied from the registry's docstrings. KaTeX, vendored same-origin (R10), renders
// it inside the elements marked .math and nowhere else — never inside Lean, code or a link — with
// trust off, so no TeX command can emit markup, and errors left as the source text. F19-T6 (R12,
// R13): explainer and annex prose is marked the same way, and the output carries MathML beside the
// rendered HTML so a screen reader reads the mathematics (KaTeX's default, stated here on purpose).
(function () {
  "use strict";
  if (typeof renderMathInElement !== "function") { return; }
  var targets = document.querySelectorAll(".math");
  Array.prototype.forEach.call(targets, function (el) {
    renderMathInElement(el, {
      delimiters: [
        { left: "$$", right: "$$", display: true },
        { left: "$", right: "$", display: false }
      ],
      throwOnError: false,
      output: "htmlAndMathml",
      trust: false,
      strict: "ignore"
    });
  });
})();
