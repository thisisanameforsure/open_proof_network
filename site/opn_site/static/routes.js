// The problem page's Routes section (F27-T3; R11). The drawing and the table are complete without
// this script. With it: the table's columns sort (click a heading; again to reverse), "Fewest open
// first" sorts by the open count and selects the first row, and hovering or selecting a row lights
// that set's statements, junctions and lines and dims the rest. Selecting changes classes only,
// never a position. Selecting the row again, or Escape, clears it and every wedge comes back.
(function () {
  "use strict";
  var section = document.querySelector(".routes-section");
  if (!section) { return; }
  var svg = section.querySelector("svg.routes-svg");
  var table = section.querySelector("table.routes-table");
  if (!svg || !table) { return; }
  var tbody = table.tBodies[0];
  var rows = Array.prototype.slice.call(tbody.querySelectorAll("tr.set-row"));
  var marks = Array.prototype.slice.call(svg.querySelectorAll("[data-sets]"));
  var wedges = Array.prototype.slice.call(svg.querySelectorAll(".wedge[data-set]"));
  var fewest = section.querySelector("button.routes-fewest");
  var hint = section.querySelector(".routes-hint");
  var state = { selected: null, hover: null, col: null, desc: false };

  function inSet(el, id) {
    return (el.getAttribute("data-sets") || "").split(" ").indexOf(id) !== -1;
  }

  function show(id) {
    svg.classList.toggle("picking", !!id);
    marks.forEach(function (el) { el.classList.toggle("lit", !!id && inSet(el, id)); });
    wedges.forEach(function (w) { w.classList.toggle("off", !!id && w.getAttribute("data-set") !== id); });
    rows.forEach(function (r) {
      var sid = r.getAttribute("data-set");
      r.classList.toggle("previewed", !!id && sid === id && sid !== state.selected);
    });
  }

  function refresh() { show(state.hover || state.selected); }

  function select(id) {
    state.selected = id;
    rows.forEach(function (r) {
      r.setAttribute("aria-selected", r.getAttribute("data-set") === id ? "true" : "false");
    });
    refresh();
  }

  rows.forEach(function (r) {
    var id = r.getAttribute("data-set");
    r.tabIndex = 0;
    r.setAttribute("aria-selected", "false");
    r.addEventListener("mouseenter", function () { state.hover = id; refresh(); });
    r.addEventListener("mouseleave", function () { state.hover = null; refresh(); });
    r.addEventListener("click", function (ev) {
      if (ev.target.closest && ev.target.closest("details")) { return; }
      select(state.selected === id ? null : id);
    });
    r.addEventListener("keydown", function (ev) {
      if (ev.key === "Enter" || ev.key === " ") {
        ev.preventDefault();
        select(state.selected === id ? null : id);
      }
    });
  });
  document.addEventListener("keydown", function (ev) {
    if (ev.key === "Escape" && state.selected) { select(null); }
  });

  // Sorting: numbers in each cell's data-sort; ties keep the record's order (data-index).
  function sortBy(col, desc) {
    var sorted = rows.slice().sort(function (a, b) {
      var x = parseFloat(a.cells[col].getAttribute("data-sort"));
      var y = parseFloat(b.cells[col].getAttribute("data-sort"));
      if (x !== y) { return desc ? y - x : x - y; }
      return parseInt(a.getAttribute("data-index"), 10) - parseInt(b.getAttribute("data-index"), 10);
    });
    sorted.forEach(function (r) { tbody.appendChild(r); });
    state.col = col;
    state.desc = desc;
    Array.prototype.forEach.call(table.tHead.rows[0].cells, function (th, i) {
      if (i === col) { th.setAttribute("aria-sort", desc ? "descending" : "ascending"); }
      else { th.removeAttribute("aria-sort"); }
    });
  }

  Array.prototype.forEach.call(table.tHead.rows[0].cells, function (th, i) {
    if (!rows.length || !rows[0].cells[i] || !rows[0].cells[i].hasAttribute("data-sort")) { return; }
    var b = document.createElement("button");
    b.type = "button";
    b.className = "routes-sort";
    while (th.firstChild) { b.appendChild(th.firstChild); }
    th.appendChild(b);
    b.addEventListener("click", function () {
      var desc = state.col === i ? !state.desc : false;
      sortBy(i, desc);
      if (fewest) { fewest.setAttribute("aria-pressed", "false"); }
    });
  });

  if (fewest) {
    fewest.hidden = false;
    fewest.addEventListener("click", function () {
      var on = fewest.getAttribute("aria-pressed") !== "true";
      fewest.setAttribute("aria-pressed", on ? "true" : "false");
      if (on) {
        sortBy(3, false);  // the Open column
        select(tbody.rows.length ? tbody.rows[0].getAttribute("data-set") : null);
      } else {
        sortBy(0, false);  // the record's order
        select(null);
      }
    });
  }
  if (hint) { hint.hidden = false; }
  // On a narrow screen the drawing scrolls in its own box; open it on the problem's own
  // statement rather than on the drawing's left edge.
  var scroller = section.querySelector(".routes-scroll");
  var top = svg.querySelector("g.rnode.root");
  if (scroller && top && scroller.scrollWidth > scroller.clientWidth) {
    var s = scroller.getBoundingClientRect(), r = top.getBoundingClientRect();
    scroller.scrollLeft += (r.left + r.width / 2) - (s.left + s.width / 2);
  }
})();
