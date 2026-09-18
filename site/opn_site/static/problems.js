// Problems filtering (F04-R7, F04-T12): the segmented control and the search box filter the
// cards and their statement rows client-side; plain JavaScript, same-origin. Without JavaScript
// the whole list is on the page and the segmented options are links carrying ?filter=.
(function () {
  "use strict";
  var list = document.querySelector(".problem-list");
  if (!list) { return; }
  var cards = Array.prototype.slice.call(list.querySelectorAll(".card.problem"));
  var opts = Array.prototype.slice.call(document.querySelectorAll(".seg-opt[data-filter]"));
  var search = document.querySelector(".search");
  var note = document.querySelector(".showing");
  var total = note ? parseInt(note.getAttribute("data-total"), 10) : cards.length;
  var filter = (new URLSearchParams(location.search).get("filter") || "all").toLowerCase();
  if (!opts.some(function (o) { return o.getAttribute("data-filter") === filter; })) { filter = "all"; }
  var query = "";
  if (search) { search.hidden = false; }

  function matchesFilter(card) {
    var status = card.getAttribute("data-status");
    if (filter === "open") { return parseInt(card.getAttribute("data-open") || "0", 10) > 0; }
    if (filter === "proved") { return status === "proved"; }
    if (filter === "unstewarded") { return status === "needs a steward"; }
    return true;
  }

  function apply() {
    var shown = 0;
    cards.forEach(function (card) {
      var ok = matchesFilter(card);
      if (ok && query) {
        var text = card.textContent.toLowerCase();
        ok = text.indexOf(query) !== -1;
      }
      card.hidden = !ok;
      if (ok) { shown += 1; }
      var rows = card.querySelectorAll(".stmt");
      Array.prototype.forEach.call(rows, function (row) {
        var keep = filter !== "open" || row.getAttribute("data-state") === "open";
        if (keep && query) {
          keep = card.textContent.toLowerCase().indexOf(query) !== -1 &&
            (row.textContent.toLowerCase().indexOf(query) !== -1 ||
             card.querySelector(".problem-top").textContent.toLowerCase().indexOf(query) !== -1);
        }
        row.hidden = !keep;
      });
    });
    opts.forEach(function (o) {
      if (o.getAttribute("data-filter") === filter) { o.setAttribute("aria-current", "true"); }
      else { o.removeAttribute("aria-current"); }
    });
    if (note) { note.textContent = "Showing " + shown + " of " + total + "."; }
  }

  opts.forEach(function (o) {
    o.addEventListener("click", function (ev) {
      ev.preventDefault();
      filter = o.getAttribute("data-filter");
      var url = filter === "all" ? location.pathname : location.pathname + "?filter=" + filter;
      history.replaceState(null, "", url);
      apply();
    });
  });
  if (search) {
    search.addEventListener("input", function () {
      query = search.value.trim().toLowerCase();
      apply();
    });
  }
  document.addEventListener("keydown", function (ev) {
    if (ev.key === "Escape" && document.activeElement && document.activeElement.classList.contains("term")) {
      document.activeElement.blur();
    }
  });
  apply();
})();
