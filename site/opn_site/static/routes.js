// The problem page's Routes section (F27-T3; R11). The drawing and the table are complete without
// this script. With it: the table's columns sort (click a heading; again to reverse), "Fewest open
// first" sorts by the open count and selects the first row, and hovering or selecting a row lights
// that set's statements, junctions and lines and dims the rest. Selecting changes classes only,
// never a position. Selecting the row again, or Escape, clears it and every wedge comes back.
// F27-T7: the first set is selected when the page loads.
// F29-T6 (R10): the drawing's "Sufficient sets" box is the selector tree; a selection is a set of
// set ids. Selecting a leaf selects its one set; selecting a branch selects every set beneath it
// (its data-sets); clicking a table row selects that one set. Every mark whose data-sets meets the
// selection is lit, the wedges of other sets dimmed, the table's rows outside the selection hidden
// and its count line says "showing n of m". Hovering a row or a box row previews it the same way.
(function () {
  "use strict";
  var section = document.querySelector(".routes-section");
  if (!section) { return; }
  var svg = section.querySelector("svg.routes-svg");
  var table = section.querySelector("table.routes-table");
  if (!svg || !table) { return; }
  var tbody = table.tBodies[0];
  var rows = Array.prototype.slice.call(tbody.querySelectorAll("tr.set-row"));
  var marks = Array.prototype.slice.call(svg.querySelectorAll("[data-node][data-sets], path[data-sets]"));
  var wedges = Array.prototype.slice.call(svg.querySelectorAll(".wedge[data-set]"));
  var selRows = Array.prototype.slice.call(svg.querySelectorAll(".sel-row[data-sets]"));
  var fewest = section.querySelector("button.routes-fewest");
  var hint = section.querySelector(".routes-hint");
  var showing = section.querySelector(".routes-showing");
  // selected: {key, ids} or null. key names what was pressed (a box row or a table row), so
  // pressing it again clears; ids are the sets lit, hidden-filtered and marked in the table.
  var state = { selected: null, hover: null, col: null, desc: false };

  function setsOf(el) {
    var raw = el.getAttribute("data-sets") || "";
    return raw ? raw.split(" ") : [];
  }

  function meets(el, ids) {
    return setsOf(el).some(function (s) { return ids.indexOf(s) !== -1; });
  }

  function sameSets(a, b) {
    return a.length === b.length && a.every(function (s, i) { return s === b[i]; });
  }

  // Light what the ids touch: marks and lines whose sets meet them, wedges of those sets; the
  // table's rows and the box's rows outside the selection get .previewed when previewing.
  function show(ids) {
    var on = !!ids && ids.length > 0;
    var sel = state.selected ? state.selected.ids : [];
    svg.classList.toggle("picking", on);
    marks.forEach(function (el) { el.classList.toggle("lit", on && meets(el, ids)); });
    wedges.forEach(function (w) { w.classList.toggle("off", on && ids.indexOf(w.getAttribute("data-set")) === -1); });
    rows.forEach(function (r) {
      var sid = r.getAttribute("data-set");
      r.classList.toggle("previewed", on && ids.indexOf(sid) !== -1 && sel.indexOf(sid) === -1);
    });
    selRows.forEach(function (g) {
      var mine = setsOf(g);
      var covered = on && mine.every(function (s) { return ids.indexOf(s) !== -1; });
      g.classList.toggle("previewed", covered && !g.classList.contains("selected"));
    });
  }

  function refresh() { show(state.hover || (state.selected ? state.selected.ids : null)); }

  // The selection: aria-selected and hidden on the table's rows, the count line, the pressed
  // box row (a leaf also reads as pressed when the selection is exactly its set).
  function select(key, ids) {
    state.selected = key ? { key: key, ids: ids } : null;
    var sel = state.selected ? state.selected.ids : [];
    var on = sel.length > 0;
    rows.forEach(function (r) {
      var sid = r.getAttribute("data-set");
      var mine = sel.indexOf(sid) !== -1;
      r.setAttribute("aria-selected", mine ? "true" : "false");
      r.hidden = on && !mine;
    });
    selRows.forEach(function (g, i) {
      var pressed = on && (("row:" + i) === state.selected.key || (g.hasAttribute("data-set") && sameSets(setsOf(g), sel)));
      g.classList.toggle("selected", pressed);
      g.setAttribute("aria-pressed", pressed ? "true" : "false");
    });
    if (showing) {
      showing.hidden = !on;
      showing.textContent = on ? "showing " + sel.length + " of " + rows.length : "";
    }
    refresh();
  }

  function toggle(key, ids) {
    if (state.selected && state.selected.key === key) { select(null, []); }
    else { select(key, ids); }
  }

  function selectSet(sid) { toggle("set:" + sid, [sid]); }

  rows.forEach(function (r) {
    var id = r.getAttribute("data-set");
    r.tabIndex = 0;
    r.setAttribute("aria-selected", "false");
    r.addEventListener("mouseenter", function () { state.hover = [id]; refresh(); });
    r.addEventListener("mouseleave", function () { state.hover = null; refresh(); });
    r.addEventListener("click", function (ev) {
      if (ev.target.closest && ev.target.closest("details")) { return; }
      selectSet(id);
    });
    r.addEventListener("keydown", function (ev) {
      if (ev.key === "Enter" || ev.key === " ") {
        ev.preventDefault();
        selectSet(id);
      }
    });
  });
  selRows.forEach(function (g, i) {
    var ids = setsOf(g);
    var key = g.hasAttribute("data-set") ? "set:" + g.getAttribute("data-set") : "row:" + i;
    g.addEventListener("mouseenter", function () { state.hover = ids; refresh(); });
    g.addEventListener("mouseleave", function () { state.hover = null; refresh(); });
    g.addEventListener("click", function () { toggle(key, ids); });
    g.addEventListener("keydown", function (ev) {
      if (ev.key === "Enter" || ev.key === " ") {
        ev.preventDefault();
        toggle(key, ids);
      }
    });
  });
  document.addEventListener("keydown", function (ev) {
    if (ev.key === "Escape" && state.selected) { select(null, []); }
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
        var first = tbody.rows.length ? tbody.rows[0].getAttribute("data-set") : null;
        select(first ? "set:" + first : null, first ? [first] : []);
      } else {
        sortBy(0, false);  // the record's order
        select(null, []);
      }
    });
  }
  if (hint) { hint.hidden = false; }
  // F27-T7: the first set listed comes selected, its routes lit.
  if (rows.length) { var sid = rows[0].getAttribute("data-set"); select("set:" + sid, [sid]); }
  // On a narrow screen the drawing scrolls in its own box; open it on the problem's own
  // statement rather than on the drawing's left edge.
  var scroller = section.querySelector(".routes-scroll");
  var top = svg.querySelector("g.rnode.root");
  if (scroller && top && scroller.scrollWidth > scroller.clientWidth) {
    var s = scroller.getBoundingClientRect(), r = top.getBoundingClientRect();
    scroller.scrollLeft += (r.left + r.width / 2) - (s.left + s.width / 2);
  }
})();
