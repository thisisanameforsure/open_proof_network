// The reading view's two orders (F22-T18, feature request N). The page is rendered dependencies
// first, every statement before the statements whose proofs use it, and that stays the default and
// the page's order without a script. The script shows two links (links, not buttons: the page
// takes no input, D-36) and, on "root first", reverses
// the statements and the table of contents, so the problem's own proof comes first and what it
// rests on follows. Nothing is fetched and nothing is stored.
(function () {
  "use strict";
  var box = document.querySelector(".rv-order");
  var list = document.querySelector(".rv-nodes");
  var toc = document.querySelector(".rv-toc ol");
  var heading = document.querySelector("[data-order-heading]");
  var cue = document.querySelector("[data-order-cue]");
  if (!box || !list) { return; }
  var words = {
    deps: [heading ? heading.textContent : "", cue ? cue.textContent : ""],
    root: [
      "The proof, root first",
      "Each statement comes before the statements its proof uses: the problem's own first."
    ]
  };
  var current = "deps";
  function reverse(el) {
    if (!el) { return; }
    var items = Array.prototype.slice.call(el.children);
    items.reverse().forEach(function (item) { el.appendChild(item); });
  }
  var buttons = box.querySelectorAll("a[data-order]");
  Array.prototype.forEach.call(buttons, function (button) {
    button.addEventListener("click", function (event) {
      event.preventDefault();
      var order = button.getAttribute("data-order");
      if (order === current || !words[order]) { return; }
      reverse(list);
      reverse(toc);
      current = order;
      if (heading) { heading.textContent = words[order][0]; }
      if (cue) { cue.textContent = words[order][1]; }
      Array.prototype.forEach.call(buttons, function (b) {
        if (b === button) { b.setAttribute("aria-current", "true"); } else { b.removeAttribute("aria-current"); }
      });
    });
  });
  box.hidden = false;
})();
