// Problems (F34-T5, R7): search, status, steward, sort, area and "needs words", each a URL query
// parameter so a view can be linked; the waiting table is paged fifty at a time. Plain JavaScript,
// same-origin. Without it every row is on the page and the controls stay hidden. The old
// ?filter= links keep working: open, proved, unstewarded and words map onto the new parameters.
(function () {
  "use strict";
  var controls = document.querySelectorAll("[data-filters]");
  var worked = document.querySelector('[data-section="worked"]');
  var waiting = document.querySelector('[data-section="waiting"]');
  if (!worked || !waiting) { return; }
  var list = worked.querySelector(".prows");
  var rowsW = Array.prototype.slice.call(worked.querySelectorAll("[data-id]"));
  var rowsQ = Array.prototype.slice.call(waiting.querySelectorAll("[data-id]"));
  var table = waiting.querySelector("table.waiting");
  var pageSize = parseInt((table && table.getAttribute("data-page-size")) || "50", 10);
  var more = waiting.querySelector("[data-more]");
  var showing = waiting.querySelector("[data-showing]");
  var form = {
    q: document.querySelector('[name="q"]'),
    status: document.querySelector('[name="status"]'),
    steward: document.querySelector('[name="steward"]'),
    sort: document.querySelector('[name="sort"]')
  };
  var chips = Array.prototype.slice.call(document.querySelectorAll("button[data-area]"));
  var wordsChip = document.querySelector("button[data-flag=words]");
  var SORT_WORDS = { recent: "most recent activity", open: "most statements open", name: "name" };
  var state = { q: "", status: "", steward: "", sort: "recent", area: "", words: false, open: false };
  var shownWaiting = pageSize;

  function read() {
    var p = new URLSearchParams(location.search);
    state.q = p.get("q") || "";
    state.status = p.get("status") || "";
    state.steward = p.get("steward") || "";
    state.sort = p.get("sort") || "recent";
    state.area = p.get("area") || "";
    state.words = p.get("words") === "1";
    state.open = p.get("open") === "1";
    var legacy = (p.get("filter") || "").toLowerCase();
    if (legacy === "open") { state.open = true; }
    if (legacy === "proved") { state.status = "proved"; }
    if (legacy === "unstewarded") { state.steward = "needs"; }
    if (legacy === "words") { state.words = true; }
    if (!SORT_WORDS[state.sort]) { state.sort = "recent"; }
  }

  function write() {
    var p = new URLSearchParams();
    if (state.q) { p.set("q", state.q); }
    if (state.status) { p.set("status", state.status); }
    if (state.steward) { p.set("steward", state.steward); }
    if (state.sort !== "recent") { p.set("sort", state.sort); }
    if (state.area) { p.set("area", state.area); }
    if (state.words) { p.set("words", "1"); }
    if (state.open) { p.set("open", "1"); }
    var s = p.toString();
    history.replaceState(null, "", location.pathname + (s ? "?" + s : ""));
  }

  function matches(row) {
    var a = function (k) { return row.getAttribute("data-" + k) || ""; };
    if (state.status && a("stage") !== state.status) { return false; }
    if (state.steward && a("steward") !== state.steward) { return false; }
    if (state.area && a("area") !== state.area) { return false; }
    if (state.words && !(parseInt(a("words") || "0", 10) > 0)) { return false; }
    if (state.open && !(parseInt(a("open") || "0", 10) > 0)) { return false; }
    if (state.q) {
      var q = state.q.toLowerCase();
      if ((a("id") + " " + row.textContent).toLowerCase().indexOf(q) === -1) { return false; }
    }
    return true;
  }

  function order(rows) {
    var by = {
      recent: function (x, y) {
        var d = (y.getAttribute("data-last") || "").localeCompare(x.getAttribute("data-last") || "");
        return d || x.getAttribute("data-name").localeCompare(y.getAttribute("data-name"));
      },
      open: function (x, y) {
        var d = parseInt(y.getAttribute("data-open") || "0", 10) - parseInt(x.getAttribute("data-open") || "0", 10);
        return d || x.getAttribute("data-name").localeCompare(y.getAttribute("data-name"));
      },
      name: function (x, y) { return x.getAttribute("data-name").localeCompare(y.getAttribute("data-name")); }
    };
    return rows.slice().sort(by[state.sort]);
  }

  function apply() {
    var w = 0;
    order(rowsW).forEach(function (row) {
      var ok = matches(row);
      row.hidden = !ok;
      if (ok) { w += 1; }
      list.appendChild(row);
    });
    var hits = rowsQ.filter(matches);
    rowsQ.forEach(function (row) { row.hidden = true; });
    hits.slice(0, shownWaiting).forEach(function (row) { row.hidden = false; });
    worked.querySelector("[data-count]").textContent = String(w);
    worked.querySelector("[data-noun]").textContent = w === 1 ? "problem" : "problems";
    waiting.querySelector("[data-noun]").textContent = hits.length === 1 ? "problem" : "problems";
    worked.querySelector("[data-sort-words]").textContent = SORT_WORDS[state.sort];
    waiting.querySelector("[data-count]").textContent = String(hits.length);
    var visible = Math.min(hits.length, shownWaiting);
    if (showing) { showing.textContent = "Showing " + visible + " of " + hits.length; }
    if (more) {
      var left = hits.length - visible;
      more.hidden = left <= 0;
      more.textContent = "Show " + Math.min(pageSize, left) + " more";
    }
    chips.forEach(function (c) { c.setAttribute("aria-pressed", String(c.getAttribute("data-area") === state.area)); });
    if (wordsChip) { wordsChip.setAttribute("aria-pressed", String(state.words)); }
  }

  function sync() {
    form.q.value = state.q;
    form.status.value = state.status;
    form.steward.value = state.steward;
    form.sort.value = state.sort;
  }

  read();
  Array.prototype.forEach.call(controls, function (c) { c.hidden = false; });
  sync();
  form.q.addEventListener("input", function () { state.q = form.q.value.trim(); shownWaiting = pageSize; write(); apply(); });
  ["status", "steward", "sort"].forEach(function (k) {
    form[k].addEventListener("change", function () { state[k] = form[k].value; shownWaiting = pageSize; write(); apply(); });
  });
  chips.forEach(function (c) {
    c.addEventListener("click", function () { state.area = c.getAttribute("data-area"); shownWaiting = pageSize; write(); apply(); });
  });
  if (wordsChip) {
    wordsChip.addEventListener("click", function () { state.words = !state.words; shownWaiting = pageSize; write(); apply(); });
  }
  if (more) {
    more.addEventListener("click", function () { shownWaiting += pageSize; apply(); });
  }
  if (state.open || location.search.indexOf("filter=") !== -1) { write(); }
  apply();
})();
