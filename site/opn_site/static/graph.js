// The problem page's statement graph (F30-T3; R3, R7, R8), replacing problem.js (F04-T12, T33,
// F18-T2) and routes.js (F27-T3, F29-T6). Without this script the page is complete: the drawing
// shows the routes layout, every pill is a link to its statement's record page, the root's
// panel is shown, the selector tree and the whole sets table are present. With it:
//   - clicking a pill selects its statement's panel and records it in the hash (#node=<id>);
//     hovering or focusing one lights its lines and the statements they join, nothing moves (R3);
//   - clicking a selector node or edge (or a table row) moves the drawing to that view: what
//     the view drops fades out, what stays slides to its place in the view's layout (embedded
//     in #graph-layouts) and the drawing resizes, what the view adds fades in; clicking the
//     pressed element again, or Escape, returns to the routes layout; the hash carries the view
//     (view=<key>); under prefers-reduced-motion the drawing changes in one step (R7);
//   - hovering or focusing a selector node, edge or table row previews it: the view's nodes
//     and lines lit, the rest dimmed, no coordinate changed (R8);
//   - the view-toggle shows the statements on no route (the all layout) and the superseded
//     toggle hides superseded statements; the table sorts, filters to the shown view's sets
//     ("showing n of m") and "Fewest open first" selects the first row's view (R4, R9).
// Every position written here is a coordinate from #graph-layouts, and a line's final d is built
// the way dag.path_d builds the markup's, so the drawing at rest is always a layout as rendered.
(function () {
  "use strict";
  var svg = document.querySelector("svg.dag");
  if (!svg) { return; }
  var ROUTES = "routes", ALL = "all";
  var FADE_MS = 200, MOVE_MS = 400, PER_SEGMENT = 16, SAMPLES = 48;
  var reduced = !!(window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches);

  function slice(list) { return Array.prototype.slice.call(list); }

  var layouts = null;
  var layoutsEl = document.getElementById("graph-layouts");
  if (layoutsEl) {
    try { layouts = JSON.parse(layoutsEl.textContent); } catch (err) { layouts = null; }
  }
  var panels = slice(document.querySelectorAll(".panel[data-node]"));
  var pills = slice(svg.querySelectorAll("g.node"));
  var marks = slice(svg.querySelectorAll("[data-node]"));  // statements and junctions
  var edges = slice(svg.querySelectorAll("path.edge"));
  var selector = document.querySelector("svg.selector");
  var choices = selector ? slice(selector.querySelectorAll("[data-view]")) : [];
  var notes = slice(document.querySelectorAll(".proof-note[data-view]"));
  var table = document.querySelector("table.routes-table");
  var tbody = table && table.tBodies.length ? table.tBodies[0] : null;
  var rows = tbody ? slice(tbody.querySelectorAll("tr.set-row")) : [];
  var showing = document.querySelector(".routes-showing");
  var fewest = document.querySelector("button.routes-fewest");
  var viewToggle = document.querySelector("button.view-toggle[data-view]");
  var state = {
    node: null,
    view: svg.getAttribute("data-view") || ROUTES,
    hover: null,
    fewestView: null,
    col: null,
    desc: false
  };

  function has(view) { return !!(view && layouts && layouts[view]); }
  function nodeIn(lay, id) { return Object.prototype.hasOwnProperty.call(lay.nodes, id); }
  function linesOf(lay) {
    var out = {};
    lay.lines.forEach(function (l) { out[l[0] + ">" + l[1]] = l[3]; });
    return out;
  }
  function idOf(g) { return g.getAttribute("data-node"); }
  function keyOf(e) { return e.getAttribute("data-key"); }

  // -- the panel (R3, as problem.js) ----------------------------------------------------------

  function select(id) {
    var found = false;
    panels.forEach(function (p) {
      var on = p.getAttribute("data-node") === id;
      p.hidden = !on;
      if (on) { found = true; }
    });
    if (!found) { return false; }
    pills.forEach(function (g) { g.classList.toggle("selected", idOf(g) === id); });
    state.node = id;
    return true;
  }

  function writeHash() {
    var parts = [];
    if (state.node) { parts.push("node=" + encodeURIComponent(state.node)); }
    if (state.view !== ROUTES) { parts.push("view=" + encodeURIComponent(state.view)); }
    history.replaceState(null, "", parts.length ? "#" + parts.join("&") : location.pathname);
  }

  function fromHash() {
    var out = { node: null, view: null };
    location.hash.replace(/^#/, "").split("&").forEach(function (part) {
      var m = /^(node|view)=(.+)$/.exec(part);
      if (m) { out[m[1]] = decodeURIComponent(m[2]); }
    });
    return out;
  }

  // -- the path builder (dag.path_d): a cubic between rows, a straight run through one --------

  function num(v) {
    var s = (Math.round(v * 10) / 10).toFixed(1);
    return s.slice(-2) === ".0" ? s.slice(0, -2) : s;
  }

  function pathD(pts) {
    var out = "M" + num(pts[0][0]) + " " + num(pts[0][1]);
    for (var i = 1; i < pts.length; i++) {
      var p = pts[i - 1], q = pts[i];
      if (p[0] === q[0]) {
        out += "V" + num(q[1]);
      } else {
        var mid = (p[1] + q[1]) / 2;
        out += "C" + [p[0], mid, q[0], mid, q[0], q[1]].map(num).join(" ");
      }
    }
    return out;
  }

  // The drawn curve as a polyline (dag.curve_points), then resampled to a fixed count by arc
  // length, so two views' versions of one line can be interpolated point for point.
  function sampled(pts) {
    var out = [pts[0]];
    for (var i = 1; i < pts.length; i++) {
      var a = pts[i - 1], b = pts[i];
      if (a[0] === b[0]) { out.push(b); continue; }
      var mid = (a[1] + b[1]) / 2;
      for (var k = 1; k <= PER_SEGMENT; k++) {
        var t = k / PER_SEGMENT, s = 1 - t;
        out.push([
          s * s * s * a[0] + 3 * s * s * t * a[0] + 3 * s * t * t * b[0] + t * t * t * b[0],
          s * s * s * a[1] + 3 * s * s * t * mid + 3 * s * t * t * mid + t * t * t * b[1]
        ]);
      }
    }
    return out;
  }

  function resample(poly, n) {
    var lens = [0], i;
    for (i = 1; i < poly.length; i++) {
      var dx = poly[i][0] - poly[i - 1][0], dy = poly[i][1] - poly[i - 1][1];
      lens.push(lens[i - 1] + Math.sqrt(dx * dx + dy * dy));
    }
    var total = lens[lens.length - 1], out = [], j = 0;
    for (var k = 0; k < n; k++) {
      if (total === 0) { out.push(poly[0]); continue; }
      var s = total * k / (n - 1);
      while (j < lens.length - 2 && lens[j + 1] < s) { j++; }
      var span = lens[j + 1] - lens[j];
      var u = span > 0 ? (s - lens[j]) / span : 0;
      out.push([lerp(poly[j][0], poly[j + 1][0], u), lerp(poly[j][1], poly[j + 1][1], u)]);
    }
    return out;
  }

  function lerp(a, b, u) { return a + (b - a) * u; }
  function ease(t) { return t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2; }

  function polyD(a, b, u) {
    var out = "";
    for (var i = 0; i < a.length; i++) {
      out += (i ? "L" : "M") + lerp(a[i][0], b[i][0], u) + " " + lerp(a[i][1], b[i][1], u);
    }
    return out;
  }

  function translate(xy) { return "translate(" + xy[0] + "," + xy[1] + ")"; }
  function size(w, h) {
    svg.setAttribute("width", w);
    svg.setAttribute("height", h);
    svg.setAttribute("viewBox", "0 0 " + w + " " + h);
  }

  // The "variants and specs" divider and label (dag.GROUP_LABEL), drawn for the opening layout
  // when it has a loose group: moved to a layout's group_y, or not drawn when it has none.
  var divider = svg.querySelector("line.dag-divider");
  var groupLabel = svg.querySelector("text.dag-group");
  function placeGroup(lay) {
    var on = typeof lay.group_y === "number";
    if (divider) {
      divider.classList.toggle("off-view", !on);
      if (on) {
        divider.setAttribute("y1", lay.group_y - 22);
        divider.setAttribute("y2", lay.group_y - 22);
        divider.setAttribute("x2", lay.w - parseFloat(divider.getAttribute("x1")));
      }
    }
    if (groupLabel) {
      groupLabel.classList.toggle("off-view", !on);
      if (on) {
        groupLabel.setAttribute("x", Math.floor(lay.w / 2));
        groupLabel.setAttribute("y", lay.group_y);
      }
    }
  }

  // -- the transition (R7) ----------------------------------------------------------------------

  var anim = { to: null, raf: 0, timers: [] };

  function clearAnim() {
    anim.timers.forEach(clearTimeout);
    anim.timers = [];
    if (anim.raf) { cancelAnimationFrame(anim.raf); }
    anim.raf = 0;
  }

  // Every element at the view's layout in one step: positions, lines, size, what is drawn.
  function place(to) {
    var lay = layouts[to], lines = linesOf(lay);
    marks.forEach(function (g) {
      var id = idOf(g);
      if (nodeIn(lay, id)) {
        g.setAttribute("transform", translate(lay.nodes[id]));
        g.classList.remove("off-view");
      } else {
        g.classList.add("off-view");
      }
      g.classList.remove("fading");
    });
    edges.forEach(function (e) {
      var key = keyOf(e);
      if (lines[key]) {
        e.setAttribute("d", pathD(lines[key]));
        e.classList.remove("off-view");
      } else {
        e.classList.add("off-view");
      }
      e.classList.remove("fading");
    });
    size(lay.w, lay.h);
    placeGroup(lay);
    svg.classList.remove("moving");
  }

  function finishPending() {
    if (!anim.to) { return; }
    var to = anim.to;
    anim.to = null;
    clearAnim();
    place(to);
    settle(to);
  }

  function transition(to, instant) {
    if (!has(to)) { return false; }
    finishPending();
    var from = state.view;
    if (to === from) { settle(to, instant); return true; }
    if (instant || reduced || !has(from)) {
      place(to);
      settle(to, instant);
      return true;
    }
    var A = layouts[from], B = layouts[to], la = linesOf(A), lb = linesOf(B);
    var leaving = [], staying = [], movingLines = [], entering = [];
    marks.forEach(function (g) {
      var id = idOf(g), inA = nodeIn(A, id), inB = nodeIn(B, id);
      if (inA && !inB) { leaving.push(g); }
      else if (inA && inB) { staying.push({ el: g, a: A.nodes[id], b: B.nodes[id] }); }
      else if (inB) { entering.push(g); }
    });
    edges.forEach(function (e) {
      var key = keyOf(e), inA = !!la[key], inB = !!lb[key];
      if (inA && !inB) { leaving.push(e); }
      else if (inA && inB) { movingLines.push({ el: e, a: la[key], b: lb[key] }); }
      else if (inB) { entering.push(e); }
    });
    anim.to = to;
    svg.classList.add("moving");

    // Phase 1: what the view drops fades out, then is not drawn.
    leaving.forEach(function (el) { el.classList.add("fading"); });
    anim.timers.push(setTimeout(function () {
      leaving.forEach(function (el) { el.classList.add("off-view"); el.classList.remove("fading"); });
      move();
    }, leaving.length ? FADE_MS : 0));

    // Phase 2: what stays slides, each line resampled to a common count, the svg resized.
    function move() {
      var lines = movingLines.map(function (l) {
        return { el: l.el, a: resample(sampled(l.a), SAMPLES), b: resample(sampled(l.b), SAMPLES) };
      });
      var start = null;
      function frame(now) {
        if (start === null) { start = now; }
        var t = Math.min(1, (now - start) / MOVE_MS), u = ease(t);
        staying.forEach(function (n) {
          n.el.setAttribute("transform", translate([lerp(n.a[0], n.b[0], u), lerp(n.a[1], n.b[1], u)]));
        });
        lines.forEach(function (l) { l.el.setAttribute("d", polyD(l.a, l.b, u)); });
        size(lerp(A.w, B.w, u), lerp(A.h, B.h, u));
        if (t < 1) { anim.raf = requestAnimationFrame(frame); }
        else { anim.raf = 0; arrive(); }
      }
      if (staying.length || lines.length || A.w !== B.w || A.h !== B.h) {
        anim.raf = requestAnimationFrame(frame);
      } else {
        arrive();
      }
    }

    // Phase 3: the final coordinates from the layout, then what the view adds fades in.
    function arrive() {
      staying.forEach(function (n) { n.el.setAttribute("transform", translate(n.b)); });
      movingLines.forEach(function (l) { l.el.setAttribute("d", pathD(l.b)); });
      entering.forEach(function (el) {
        if (el.hasAttribute("data-node")) { el.setAttribute("transform", translate(B.nodes[idOf(el)])); }
        else { el.setAttribute("d", pathD(lb[keyOf(el)])); }
        el.classList.add("fading");
        el.classList.remove("off-view");
      });
      size(B.w, B.h);
      placeGroup(B);
      void svg.getBoundingClientRect();  // flush, so the fade runs from 0
      entering.forEach(function (el) { el.classList.remove("fading"); });
      anim.timers.push(setTimeout(function () {
        anim.to = null;
        svg.classList.remove("moving");
        settle(to);
      }, entering.length ? FADE_MS : 0));
    }
    return true;
  }

  // The sets a view covers: its selector element's data-sets, or a table row's one set; null
  // for routes and all (no filter).
  function setsOf(view) {
    for (var i = 0; i < choices.length; i++) {
      if (choices[i].getAttribute("data-view") === view) {
        var raw = choices[i].getAttribute("data-sets") || "";
        return raw ? raw.split(" ") : [];
      }
    }
    for (var j = 0; j < rows.length; j++) {
      if (rows[j].getAttribute("data-view") === view) { return [rows[j].getAttribute("data-set")]; }
    }
    return null;
  }

  // The view is shown: data-view on the svg, the pressed element, the table's rows and count
  // line, the proof note, the view-toggle, the hash (left alone on load, keepHash).
  function settle(to, keepHash) {
    state.view = to;
    svg.setAttribute("data-view", to);
    var sets = setsOf(to), shown = 0;
    choices.forEach(function (c) {
      var on = c.getAttribute("data-view") === to;
      c.setAttribute("aria-pressed", on ? "true" : "false");
      c.classList.toggle("selected", on);
    });
    rows.forEach(function (r) {
      var mine = !sets || sets.indexOf(r.getAttribute("data-set")) !== -1;
      r.hidden = !mine;
      r.setAttribute("aria-selected", sets && mine ? "true" : "false");
      if (mine) { shown++; }
    });
    if (showing) {
      showing.hidden = !sets;
      showing.textContent = sets ? "showing " + shown + " of " + rows.length : "";
    }
    notes.forEach(function (n) { n.hidden = n.getAttribute("data-view") !== to; });
    if (viewToggle) {
      var all = to === ALL;
      viewToggle.setAttribute("aria-pressed", all ? "true" : "false");
      viewToggle.textContent = all ? toggleWords.shown : toggleWords.plain;
    }
    if (fewest && to !== state.fewestView) {
      state.fewestView = null;
      fewest.setAttribute("aria-pressed", "false");
    }
    if (!keepHash) { writeHash(); }
    refreshLit();
  }

  // Press: the view, or routes again when it is the one shown.
  function choose(view) {
    if (!has(view)) { return; }
    transition(view === state.view ? ROUTES : view);
  }

  // -- previews (R8) and the pill hover (R3) ---------------------------------------------------

  function clearLit() {
    marks.forEach(function (g) { g.classList.remove("lit"); });
    edges.forEach(function (e) { e.classList.remove("lit"); });
  }

  function refreshLit() {
    var v = state.hover;
    choices.forEach(function (c) {
      c.classList.toggle("previewed", !!v && c.getAttribute("data-view") === v && !c.classList.contains("selected"));
    });
    var sets = v ? setsOf(v) : null;
    rows.forEach(function (r) {
      r.classList.toggle("previewed", !!sets && sets.indexOf(r.getAttribute("data-set")) !== -1
        && r.getAttribute("aria-selected") !== "true");
    });
    if (!has(v)) {
      svg.classList.remove("picking");
      if (!svg.classList.contains("hovering")) { clearLit(); }
      return;
    }
    var lay = layouts[v], lines = linesOf(lay);
    svg.classList.add("picking");
    marks.forEach(function (g) { g.classList.toggle("lit", nodeIn(lay, idOf(g))); });
    edges.forEach(function (e) { e.classList.toggle("lit", !!lines[keyOf(e)]); });
  }

  function preview(view) {
    state.hover = has(view) ? view : null;
    refreshLit();
  }

  // F04-T33: hovering or focusing a statement lights its lines and the statements they join,
  // and dims the rest of the drawing; nothing moves.
  function light(id) {
    var near = {};
    near[id] = true;
    edges.forEach(function (e) {
      var from = e.getAttribute("data-from"), to = e.getAttribute("data-to");
      var on = !e.classList.contains("off-view") && (from === id || to === id);
      e.classList.toggle("lit", on);
      if (on) { near[from] = true; near[to] = true; }
    });
    marks.forEach(function (g) { g.classList.toggle("lit", !!near[idOf(g)]); });
    svg.classList.add("hovering");
  }

  function unlight() {
    svg.classList.remove("hovering");
    clearLit();
    refreshLit();
  }

  pills.forEach(function (g) {
    var link = g.parentNode;
    g.addEventListener("click", function (ev) {
      if (select(idOf(g))) {
        ev.preventDefault();
        writeHash();
      }
    });
    link.addEventListener("mouseenter", function () { light(idOf(g)); });
    link.addEventListener("mouseleave", unlight);
    link.addEventListener("focusin", function () { light(idOf(g)); });
    link.addEventListener("focusout", unlight);
  });

  // -- the selector (R5, R7, R8) ----------------------------------------------------------------

  function pressable(el, view) {
    var hit = el.parentNode && el.parentNode.tagName && el.parentNode.tagName.toLowerCase() === "a" ? el.parentNode : el;
    hit.addEventListener("click", function (ev) { ev.preventDefault(); choose(view); });
    hit.addEventListener("mouseenter", function () { preview(view); });
    hit.addEventListener("mouseleave", function () { preview(null); });
    hit.addEventListener("focusin", function () { preview(view); });
    hit.addEventListener("focusout", function () { preview(null); });
    el.addEventListener("keydown", function (ev) {
      if (ev.key === "Enter" || ev.key === " ") {
        ev.preventDefault();
        ev.stopPropagation();
        choose(view);
      }
    });
  }

  choices.forEach(function (c) { pressable(c, c.getAttribute("data-view")); });

  rows.forEach(function (r) {
    var view = r.getAttribute("data-view");
    if (!has(view)) { return; }
    r.tabIndex = 0;
    r.setAttribute("aria-selected", "false");
    r.addEventListener("mouseenter", function () { preview(view); });
    r.addEventListener("mouseleave", function () { preview(null); });
    r.addEventListener("focusin", function () { preview(view); });
    r.addEventListener("focusout", function () { preview(null); });
    r.addEventListener("click", function (ev) {
      if (ev.target.closest && ev.target.closest("details, a")) { return; }
      choose(view);
    });
    r.addEventListener("keydown", function (ev) {
      if (ev.key === "Enter" || ev.key === " ") {
        ev.preventDefault();
        choose(view);
      }
    });
  });

  document.addEventListener("keydown", function (ev) {
    if (ev.key === "Escape" && state.view !== ROUTES) { transition(ROUTES); }
  });

  // -- the view-toggle (R4): all <-> routes --------------------------------------------------------

  var toggleWords = { plain: "", shown: "" };
  if (viewToggle && has(ALL)) {
    toggleWords.plain = viewToggle.textContent;
    toggleWords.shown = viewToggle.getAttribute("data-shown-label") || toggleWords.plain;
    viewToggle.hidden = false;
    viewToggle.addEventListener("click", function () {
      transition(state.view === ALL ? ROUTES : ALL);
    });
  }

  // F04-T33: superseded statements are faded; the toggle (rendered hidden, shown here because it
  // needs this script) hides them and their lines.
  var hideToggle = document.querySelector("button.dag-toggle[data-hide]");
  if (hideToggle) {
    var hideWords = hideToggle.textContent;
    var hiddenWords = hideToggle.getAttribute("data-shown-label");
    hideToggle.hidden = false;
    hideToggle.addEventListener("click", function () {
      var on = svg.classList.toggle("hide-superseded");
      hideToggle.setAttribute("aria-pressed", on ? "true" : "false");
      hideToggle.textContent = on ? hiddenWords : hideWords;
    });
  }

  // -- the table (F27-R11, R9): sorting, and "Fewest open first" -----------------------------------

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

  if (table && table.tHead && rows.length) {
    Array.prototype.forEach.call(table.tHead.rows[0].cells, function (th, i) {
      if (!rows[0].cells[i] || !rows[0].cells[i].hasAttribute("data-sort")) { return; }
      var b = document.createElement("button");
      b.type = "button";
      b.className = "routes-sort";
      while (th.firstChild) { b.appendChild(th.firstChild); }
      th.appendChild(b);
      b.addEventListener("click", function () {
        sortBy(i, state.col === i ? !state.desc : false);
        if (fewest) { state.fewestView = null; fewest.setAttribute("aria-pressed", "false"); }
      });
    });
  }

  if (fewest && tbody) {
    fewest.hidden = false;
    fewest.addEventListener("click", function () {
      var on = fewest.getAttribute("aria-pressed") !== "true";
      if (on) {
        sortBy(3, false);  // the Open column
        var first = tbody.rows.length ? tbody.rows[0].getAttribute("data-view") : null;
        if (has(first)) {
          state.fewestView = first;
          fewest.setAttribute("aria-pressed", "true");
          transition(first);
        }
      } else {
        sortBy(0, false);  // the record's order
        state.fewestView = null;
        fewest.setAttribute("aria-pressed", "false");
        transition(ROUTES);
      }
    });
  }

  // -- the start, and the hash ---------------------------------------------------------------------

  var initial = fromHash();
  if (!select(initial.node || (panels.length ? panels[0].getAttribute("data-node") : null)) && panels.length) {
    select(panels[0].getAttribute("data-node"));
  }
  if (has(initial.view) && initial.view !== state.view) {
    transition(initial.view, true);
  } else if (has(state.view)) {
    settle(state.view, true);
  }
  // F04-T18: a panel's "Superseded by" link is an in-page #node= link, so the hash can change
  // without a pill being clicked.
  window.addEventListener("hashchange", function () {
    var h = fromHash();
    if (h.node) { select(h.node); }
    var view = h.view || ROUTES;
    if (has(view) && view !== state.view) { transition(view); }
  });
})();
