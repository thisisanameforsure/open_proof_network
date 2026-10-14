// F04-T50: a statement's page keeps most of its record folded, so a link that lands inside a
// closed <details> (a note's full text, the statement's words, the witness) opens every fold
// around its target and scrolls to it. Runs on load and whenever the address's fragment changes.
(function () {
  "use strict";
  function reveal() {
    var id = decodeURIComponent(window.location.hash.slice(1));
    if (!id || id.indexOf("=") !== -1) return;
    var el = document.getElementById(id);
    if (!el) return;
    var opened = false;
    for (var n = el; n; n = n.parentElement) {
      if (n.tagName === "DETAILS" && !n.open) {
        n.open = true;
        opened = true;
      }
    }
    if (opened) el.scrollIntoView();
  }
  window.addEventListener("hashchange", reveal);
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", reveal);
  } else {
    reveal();
  }
})();
