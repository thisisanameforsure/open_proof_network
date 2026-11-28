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
//   - F34-T48: "Show n harder routes" adds the strictly harder routes to the picker and the List,
//     each a numbered end; the figure always draws the one route selected;
//   - the view-toggle shows the statements on no route (the all layout); superseded statements
//     are not drawn (F30-T16); F34-T47: the List is one row per route, the drawn one marked,
//     its number or "Draw" drawing it (the sets table, its sorting and filter are gone);
//   - F27-R13: "Stop at proved statements" (in the selector's panel, ticked by default) unticked
//     swaps every set view for its follow/ twin, which also holds what each proved statement's
//     proof rests on, and the table shows its followed counts; the hash carries the twin's key.
//   - F30-T11 (D-14 v3.26 as amended by v3.46): the band of proposed statements (svg.band) is a
//     drawing of its own under the main one that no selection moves. Hovering or focusing a band
//     pill lights its own lines through its junctions and the measured lines from it into the
//     tree (path.band-link in the overlay, each drawn from the two pills' boxes while lit and
//     nothing at rest); clicking keeps them lit until clicked again (band=<id> in the hash).
// Every position written here is a coordinate from #graph-layouts, and a line's final d is built
// the way dag.path_d builds the markup's, so the drawing at rest is always a layout as rendered.
(function () {
  "use strict";
  var svg = document.querySelector("svg.dag:not(.band)");
  if (!svg) { return; }
  var ROUTES = "routes";
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
  var selector = document.querySelector("svg.selector:not(.harder-picker)");
  // F34-T48 (ROUND-2 D2): the picker with the harder routes added, shown in the main one's place
  var hardSelector = document.querySelector("svg.selector.harder-picker");
  var choices = slice(document.querySelectorAll("svg.selector [data-view]"));
  var notes = slice(document.querySelectorAll(".proof-note[data-view]"));
  // F34-T47 (ROUND-2 D1): the List is one row per route (li.route-row), the picker's other face
  var rows = slice(document.querySelectorAll("li.route-row[data-view]"));
  // F34-T50 (ROUND-2 D4): the phone's row of 44px route buttons under the picker
  var routeButtons = slice(document.querySelectorAll("button.route-btn[data-view]"));
  var HARD = "hard/";  // F34-T48: a strictly harder route's own view
  var FOLLOW = "follow/";
  var followBox = document.querySelector("input.follow-proved");
  var setsGrid = document.querySelector(".sets-grid");
  var bandSvg = document.querySelector("svg.band");
  var bandMarks = bandSvg ? slice(bandSvg.querySelectorAll("[data-node]")) : [];
  var bandPills = bandSvg ? slice(bandSvg.querySelectorAll("g.node")) : [];
  var links = slice(document.querySelectorAll("path.band-link"));
  var wrap = svg.closest ? svg.closest(".dag-wrap") : null;
  // F34-T12 (R14): the view the page opens on, and comes back to — one route, the proving set
  // with the fewest open statements (data-home); a problem with no route opens on routes.
  var HOME = svg.getAttribute("data-home") || ROUTES;
  var state = {
    node: null,
    view: svg.getAttribute("data-view") || ROUTES,
    hover: null,
    follow: false,
    bandHover: null,
    band: null,
    open: null  // F34-T51: on a phone, the statement whose record is open under its row
  };

  function has(view) { return !!(view && layouts && layouts[view]); }
  // F27-R13: a set view (a selector node, leaf or edge) has a follow/ twin; the selector and the
  // table carry the plain keys, and the reading in force picks which of the two is shown.
  function base(view) {
    if (!view) { return view; }
    var b = view.indexOf(FOLLOW) === 0 ? view.slice(FOLLOW.length) : view;
    return b.replace(/~(fold\d+|open)$/, "");  // F34-T24, T47: an open fold is still its route
  }
  function isSetView(view) {
    var b = base(view);
    return !!b && (b === "sel" || b.indexOf("sel/") === 0 || b.indexOf("edge/") === 0 || b.indexOf(HARD) === 0);
  }
  function withMode(view) {
    var b = base(view);
    return state.follow && isSetView(b) && has(FOLLOW + b) ? FOLLOW + b : b;
  }
  function nodeIn(lay, id) { return Object.prototype.hasOwnProperty.call(lay.nodes, id); }
  function linesOf(lay) {
    var out = {};
    lay.lines.forEach(function (l) { out[l[0] + ">" + l[1]] = l[3]; });
    return out;
  }
  function idOf(g) { return g.getAttribute("data-node"); }
  function keyOf(e) { return e.getAttribute("data-key"); }

  // -- the panel (R3, as problem.js) ----------------------------------------------------------

  // F34-T16 (R16): a panel shows one part at a time under its tabs; Record opens its fold.
  function showTab(panel, part) {
    var tabs = panel.querySelector(".panel-tabs");
    if (!tabs) { return; }
    tabs.hidden = false;
    slice(tabs.querySelectorAll("[data-tab]")).forEach(function (b) {
      b.setAttribute("aria-selected", b.getAttribute("data-tab") === part ? "true" : "false");
    });
    // a part is a section of the panel (data-section) or its record fold
    slice(panel.querySelectorAll(".panel-sec[data-section], details.record")).forEach(function (sec) {
      var on = (sec.getAttribute("data-section") || "record") === part;
      sec.hidden = !on;
      if (on && sec.tagName.toLowerCase() === "details") { sec.open = true; }
    });
  }
  panels.forEach(function (p) {
    p.addEventListener("click", function (ev) {
      var b = ev.target.closest ? ev.target.closest(".panel-tabs [data-tab]") : null;
      if (b) { showTab(p, b.getAttribute("data-tab")); }
    });
  });
  var homeNode = null;
  panels.forEach(function (p) { if (!p.hidden && homeNode === null) { homeNode = p.getAttribute("data-node"); } });

  // F34-T16 (R16): the selected statement's path from the problem, drawn heavier. A line is on
  // it when both its ends are, a route's junction standing for the statement it splits.
  function stem(id) { return id ? id.replace(/@\d+$/, "") : id; }
  function drawPath(panel) {
    var el = panel ? panel.querySelector(".panel-path") : null;
    var ids = el && panel.getAttribute("data-node") !== homeNode
      ? (el.getAttribute("data-path") || "").split(" ").filter(Boolean) : [];
    var on = {};
    ids.forEach(function (i) { on[i] = true; });
    edges.forEach(function (e) {
      var k = (keyOf(e) || "").split(">");
      var a = stem(k[0]), b = stem(k[1]);
      e.classList.toggle("on-path", ids.length > 1 && k.length === 2 && !!on[a] && !!on[b]);
    });
  }

  function select(id) {
    var found = false, shown = null;
    panels.forEach(function (p) {
      var on = p.getAttribute("data-node") === id;
      p.hidden = !on;
      if (on) { found = true; shown = p; }
    });
    if (!found) { return false; }
    pills.forEach(function (g) { g.classList.toggle("selected", idOf(g) === id); });
    state.node = id;
    showTab(shown, "claim");
    drawPath(shown);
    drawLink();  // F34-T37
    return true;
  }

  function writeHash() {
    var parts = [];
    if (state.node) { parts.push("node=" + encodeURIComponent(state.node)); }
    if (state.view !== HOME) { parts.push("view=" + encodeURIComponent(state.view)); }
    if (state.band) { parts.push("band=" + encodeURIComponent(state.band)); }
    history.replaceState(null, "", parts.length ? "#" + parts.join("&") : location.pathname);
  }

  function fromHash() {
    var out = { node: null, view: null, band: null };
    location.hash.replace(/^#/, "").split("&").forEach(function (part) {
      var m = /^(node|view|band)=(.+)$/.exec(part);
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

  // -- the band (F30-T11) ---------------------------------------------------------------------------
  // A lit line between the band and the tree runs from the band pill's top to the tree pill's
  // bottom, in the overlay's own pixels (svg.band-links), rebuilt whenever either end moves.
  function pillOf(root, id) {
    return root ? root.querySelector('[data-node="' + id.replace(/"/g, '\\"') + '"]') : null;
  }
  // F30-T13: the band is a column at the card's right. A line from a band pill leaves its left
  // side; it meets a tree pill at the side facing the column (its top or bottom where the column
  // sits above or below the tree, on a phone), and another band pill by a curve out to the left.
  function linkD(link) {
    if (!wrap) { return ""; }
    var from = link.getAttribute("data-from"), to = link.getAttribute("data-to");
    var inBand = pillOf(bandSvg, from) ? from : to, other = inBand === from ? to : from;
    var a = pillOf(bandSvg, inBand), b = pillOf(svg, other) || pillOf(bandSvg, other);
    if (!a || !b || getComputedStyle(b).display === "none") { return ""; }
    // In the overlay's own pixels: the overlay (svg.band-links) is the path's coordinate origin.
    var host = link.ownerSVGElement || wrap;
    var w = host.getBoundingClientRect(), ra = a.getBoundingClientRect(), rb = b.getBoundingClientRect();
    var ya = ra.top + ra.height / 2 - w.top, yb = rb.top + rb.height / 2 - w.top;
    var x1, y1, x2, y2;
    if (bandSvg.contains(b)) {
      x1 = ra.left - w.left; x2 = rb.left - w.left;
      // out to the left of the column, never past the card's own left edge
      var floor = wrap.getBoundingClientRect().left - w.left + 6;
      var bulge = Math.max(floor, Math.min(x1, x2) - Math.max(18, Math.abs(yb - ya) / 3));
      return "M" + num(x1) + " " + num(ya) + "C" + [bulge, ya, bulge, yb, x2, yb].map(num).join(" ");
    }
    if (rb.right <= ra.left) {
      x1 = ra.left - w.left; y1 = ya; x2 = rb.right - w.left; y2 = yb;
      var mx = (x1 + x2) / 2;
      return "M" + num(x1) + " " + num(y1) + "C" + [mx, y1, mx, y2, x2, y2].map(num).join(" ");
    }
    x1 = ra.left + ra.width / 2 - w.left; x2 = rb.left + rb.width / 2 - w.left;
    if (rb.bottom <= ra.top) { y1 = ra.top - w.top; y2 = rb.bottom - w.top; }
    else { y1 = ra.bottom - w.top; y2 = rb.top - w.top; }
    var mid = (y1 + y2) / 2;
    return "M" + num(x1) + " " + num(y1) + "C" + [x1, mid, x2, mid, x2, y2].map(num).join(" ");
  }
  // Paint the band's state: the hovered pill, else the pinned one, else nothing.
  function applyBand() {
    var id = state.bandHover || state.band;
    var treeLit = {};
    links.forEach(function (l) {
      var mine = !!id && (l.getAttribute("data-from") === id || l.getAttribute("data-to") === id);
      var d = mine ? linkD(l) : "";
      if (d) {
        l.setAttribute("d", d);
        l.classList.add("lit");
        var other = l.getAttribute("data-from") === id ? l.getAttribute("data-to") : l.getAttribute("data-from");
        treeLit[other] = true;
      } else {
        l.removeAttribute("d");
        l.classList.remove("lit");
      }
    });
    if (bandSvg) {
      // F30-T13: the column draws no line, so its lit pills are the hovered one and the far ends
      // of its lit links.
      bandMarks.forEach(function (g) { g.classList.toggle("lit", !!id && (idOf(g) === id || !!treeLit[idOf(g)])); });
      bandSvg.classList.toggle("hovering", !!id);
      bandPills.forEach(function (g) { g.classList.toggle("pinned", idOf(g) === state.band); });
    }
    // The tree: only the lines' far ends lit and the rest dimmed (band-lit), unless a tree pill's
    // own hover is on; when the band goes dark the tree's own state is painted again.
    var any = Object.keys(treeLit).some(function (k) { return !pillOf(bandSvg, k); });
    var ownHover = svg.classList.contains("hovering") && !svg.classList.contains("band-lit");
    if (any && !ownHover) {
      marks.forEach(function (g) { g.classList.toggle("lit", !!treeLit[idOf(g)]); });
      edges.forEach(function (e) { e.classList.remove("lit"); });
      svg.classList.add("hovering");
      svg.classList.add("band-lit");
    } else if (!any && svg.classList.contains("band-lit")) {
      svg.classList.remove("band-lit");
      svg.classList.remove("hovering");
      clearLit();
      refreshLit();
    }
  }
  function redrawLinks() {
    links.forEach(function (l) {
      if (!l.classList.contains("lit")) { return; }
      var d = linkD(l);
      if (d) { l.setAttribute("d", d); } else { l.removeAttribute("d"); l.classList.remove("lit"); }
    });
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
    view = base(view);
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

  // F34-T33 (REMINDERS item 5): "Drawn below ↓ Route n · …" and the figure's caption name the route
  // a numbered end draws; any other view (a part of a route, every statement) says so instead.
  var drawnBelow = document.querySelector(".drawn-below strong");
  var figureCap = document.querySelector(".figure-cap strong");
  function routeCaption(to) {
    var plain = base(to), end = null;
    slice(document.querySelectorAll("svg.selector g.kind-leaf[data-route]")).forEach(function (g) {
      if (!end && g.getAttribute("data-view") === plain) { end = g; }
    });
    var name = end ? end.getAttribute("data-route") : "the statements of your selection";
    var count = end ? " · " + end.getAttribute("data-count") : "";
    if (drawnBelow) { drawnBelow.textContent = name + count; }
    if (figureCap) { figureCap.textContent = name + count; }
    // F34-T41: the drawn route's retire controls (shelve.js fills them for a steward or curator)
    slice(document.querySelectorAll(".figure-retire")).forEach(function (g) {
      g.hidden = g.getAttribute("data-view") !== plain;
      if (g.hidden) { g.removeAttribute("open"); }  // F34-T55: another route's choices are shut
    });
  }

  // The view is shown: data-view on the svg, the pressed element, the table's rows and count
  // line, the proof note, the view-toggle, the hash (left alone on load, keepHash).
  function settle(to, keepHash) {
    state.view = to;
    svg.setAttribute("data-view", to);
    outlineFollows(to);  // F34-T17
    routeCaption(to);  // F34-T33
    drawLink();  // F34-T37: the boxes have moved
    placePanel();  // F34-T39: on a phone, the record under its row of the outline
    var plain = base(to);
    choices.forEach(function (c) {
      var on = c.getAttribute("data-view") === plain;
      c.setAttribute("aria-pressed", on ? "true" : "false");
      c.classList.toggle("selected", on);
    });
    // F34-T47: the row of the route drawn is marked; no row is ever hidden
    rows.forEach(function (r) {
      var on = r.getAttribute("data-view") === plain;
      r.setAttribute("aria-selected", on ? "true" : "false");
      var n = r.querySelector("button.route-n");
      if (n) { n.setAttribute("aria-pressed", on ? "true" : "false"); }
    });
    figureFolds(to);
    routeButtons.forEach(function (b) {  // F34-T50
      b.setAttribute("aria-pressed", b.getAttribute("data-view") === plain ? "true" : "false");
    });
    notes.forEach(function (n) { n.hidden = n.getAttribute("data-view") !== to; });
    if (!keepHash) { writeHash(); }
    refreshLit();
    applyBand();
  }

  // Press: the view, or routes again when it is the one shown.
  function choose(view) {
    view = withMode(view);
    if (!has(view)) { return; }
    transition(view === state.view && view !== HOME ? HOME : view);
  }

  // -- previews (R8) and the pill hover (R3) ---------------------------------------------------

  function clearLit() {
    marks.forEach(function (g) { g.classList.remove("lit"); });
    edges.forEach(function (e) { e.classList.remove("lit"); });
  }

  function refreshLit() {
    var v = state.hover;
    choices.forEach(function (c) {
      c.classList.toggle("previewed", !!v && c.getAttribute("data-view") === base(v) && !c.classList.contains("selected"));
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
    view = withMode(view);
    state.hover = has(view) ? view : null;
    refreshLit();
  }

  // F04-T33: hovering or focusing a statement lights its lines and the statements they join,
  // and dims the rest of the drawing; nothing moves.
  // A route's junction is a dot on the way, not a statement: the hover reaches through it (the
  // owner, 2026-10-18), so a parent's hover lights its holes and a hole's hover its parent.
  var junction = {};
  marks.forEach(function (g) { if (g.hasAttribute("data-route")) { junction[idOf(g)] = true; } });
  function light(id) {
    var near = {}, on = {}, seen = {}, queue = [id];
    near[id] = true;
    while (queue.length) {
      var v = queue.shift();
      if (seen[v]) { continue; }
      seen[v] = true;
      edges.forEach(function (e) {
        if (e.classList.contains("off-view")) { return; }
        var from = e.getAttribute("data-from"), to = e.getAttribute("data-to");
        if (from !== v && to !== v) { return; }
        on[keyOf(e)] = true;
        var other = from === v ? to : from;
        near[other] = true;
        if (junction[other] && !seen[other]) { queue.push(other); }
      });
    }
    edges.forEach(function (e) { e.classList.toggle("lit", !!on[keyOf(e)]); });
    marks.forEach(function (g) { g.classList.toggle("lit", !!near[idOf(g)]); });
    svg.classList.add("hovering");
  }

  function unlight() {
    svg.classList.remove("hovering");
    svg.classList.remove("band-lit");
    clearLit();
    refreshLit();
    applyBand();
  }

  // F34-T27: the outline's "+ n speculative ↓" scrolls to its group; the hash keeps the view
  // F34-T55: so does the line under the drawing for the statements on no route (a bare hash
  // would read as "no view" and put the home route back)
  slice(document.querySelectorAll("a.spec-more, .off-route-line a")).forEach(function (a) {
    a.addEventListener("click", function (ev) {
      var group = document.getElementById(a.getAttribute("href").slice(1));
      if (group) { ev.preventDefault(); group.scrollIntoView({ block: "start" }); }
    });
  });

  pills.forEach(function (g) {
    var link = g.parentNode;
    g.addEventListener("click", function (ev) {
      // F34-T27: "+ n speculative ↓" scrolls to its group in §2; the view and the hash stay
      // F34-T42: "uses: …" selects the statement it names into the panel
      var uses = ev.target.closest ? ev.target.closest(".uses-chip") : null;
      if (uses) {
        ev.preventDefault();
        if (select(uses.getAttribute("data-uses"))) { state.open = state.node; writeHash(); placePanel(); }
        return;
      }
      var chip = ev.target.closest ? ev.target.closest(".spec-chip") : null;
      if (chip) {
        ev.preventDefault();
        var group = document.getElementById(chip.getAttribute("data-to"));
        if (group) { group.scrollIntoView({ block: "start" }); }
        return;
      }
      // F34-T24 (R15): a fold opens in place — the drawing moves to the view with it open
      if (g.classList.contains("fold")) {
        ev.preventDefault();
        var open = g.getAttribute("data-open");
        if (has(open)) { transition(open); }
        return;
      }
      if (select(idOf(g))) {
        ev.preventDefault();
        writeHash();
      }
    });
    link.addEventListener("mouseenter", function () { svg.classList.remove("band-lit"); light(idOf(g)); });
    link.addEventListener("mouseleave", unlight);
    link.addEventListener("focusin", function () { svg.classList.remove("band-lit"); light(idOf(g)); });
    link.addEventListener("focusout", unlight);
  });

  // F30-T11: a band pill previews on hover, pins on click (and selects its panel), unpins on a
  // second click; the lines follow the tree when a selection moves it.
  function bandHover(id) { state.bandHover = id; applyBand(); }
  bandPills.forEach(function (g) {
    var link = g.parentNode;
    var id = idOf(g);
    g.addEventListener("click", function (ev) {
      ev.preventDefault();
      ev.stopPropagation();  // F30-T14: the document's click below clears a pin; this one sets it
      select(id);
      state.band = state.band === id ? null : id;
      writeHash();
      applyBand();
    });
    link.addEventListener("mouseenter", function () { bandHover(id); });
    link.addEventListener("mouseleave", function () { bandHover(null); });
    link.addEventListener("focusin", function () { bandHover(id); });
    link.addEventListener("focusout", function () { bandHover(null); });
  });
  // F30-T14 (the owner, 2026-10-22: "I don't see how to deselect"): a pinned spec clears on a
  // click on empty space and on Escape, as well as on a second click on itself. A click on
  // anything that does something (a pill, a selector node, a link, a control) keeps the pin,
  // so a spec's lines can follow the tree through a selection (F30-T11).
  function unpin() {
    if (!state.band) { return; }
    state.band = null;
    writeHash();
    applyBand();
  }
  if (bandPills.length) {
    document.addEventListener("click", function (ev) {
      var t = ev.target;
      if (t && t.closest && t.closest("a, button, input, label, select, [data-node], [data-view], [data-key]")) { return; }
      unpin();
    });
    document.addEventListener("keydown", function (ev) { if (ev.key === "Escape") { unpin(); } });
  }
  if (links.length) {
    window.addEventListener("resize", redrawLinks);
    var scroller = svg.parentNode;
    if (scroller) { scroller.addEventListener("scroll", redrawLinks); }
    if (bandSvg && bandSvg.parentNode) { bandSvg.parentNode.addEventListener("scroll", redrawLinks); }
  }

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

  // T8 (the owner, 2026-10-18): the selector has the drawing's own hover — the node, its lines
  // and the nodes they join lit, the rest of the selector dimmed — and its words in a tooltip,
  // since the tree draws none. The preview on the drawing (above) runs beside it.
  var selNodes = slice(document.querySelectorAll("svg.selector g.sel-node"));
  var selEdges = slice(document.querySelectorAll("svg.selector path.sel-edge"));
  var selWrap = selector ? selector.parentNode : null;
  var tip = selWrap ? selWrap.querySelector(".sel-tip") : null;
  function selKey(g) { return g.getAttribute("data-key"); }
  function selLight(keys, words, anchor) {
    var near = {}, own = anchor.ownerSVGElement;
    keys.forEach(function (k) { near[k] = true; });
    selEdges.forEach(function (e) {
      if (e.ownerSVGElement !== own) { return; }
      var from = e.getAttribute("data-from"), to = e.getAttribute("data-to");
      var on = keys.indexOf(from) !== -1 || keys.indexOf(to) !== -1;
      e.classList.toggle("lit", on);
      if (on) { near[from] = true; near[to] = true; }
    });
    selNodes.forEach(function (g) { g.classList.toggle("lit", g.ownerSVGElement === own && !!near[selKey(g)]); });
    own.classList.add("hovering");
    if (tip && words) {
      tip.textContent = words;
      tip.hidden = false;
      // To the right of the tree, level with the node, so it never covers the tree itself.
      var w = selWrap.getBoundingClientRect(), a = anchor.getBoundingClientRect();
      var sv = own.getBoundingClientRect();
      tip.style.left = Math.max(0, Math.min(sv.right - w.left + 10, w.width - 260)) + "px";
      tip.style.top = Math.max(0, a.top - w.top - 4) + "px";
    }
  }
  function selUnlight() {
    if (selector) { selector.classList.remove("hovering"); }
    if (hardSelector) { hardSelector.classList.remove("hovering"); }
    selNodes.forEach(function (g) { g.classList.remove("lit"); });
    selEdges.forEach(function (e) { e.classList.remove("lit"); });
    if (tip) { tip.hidden = true; }
  }
  selNodes.forEach(function (g) {
    var hit = g.parentNode && g.parentNode.tagName.toLowerCase() === "a" ? g.parentNode : g;
    hit.addEventListener("mouseenter", function () { selLight([selKey(g)], g.getAttribute("data-words"), g); });
    hit.addEventListener("mouseleave", selUnlight);
    hit.addEventListener("focusin", function () { selLight([selKey(g)], g.getAttribute("data-words"), g); });
    hit.addEventListener("focusout", selUnlight);
  });
  // T9 (the owner): the neighbour lighting is for nodes only; an edge keeps its own hover
  // stroke and the preview it casts on the drawing.

  // F34-T47: a row's number, or its "Draw", draws the route (and never undraws it); hovering the
  // row previews it on the drawing, as hovering its numbered end does.
  function draw(view) {
    view = withMode(view);
    if (has(view) && base(state.view) !== base(view)) { transition(view); }
  }
  rows.forEach(function (r) {
    var view = r.getAttribute("data-view");
    if (!has(view)) { return; }
    r.addEventListener("mouseenter", function () { preview(view); });
    r.addEventListener("mouseleave", function () { preview(null); });
    slice(r.querySelectorAll("button.route-n, a.route-draw")).forEach(function (b) {
      b.addEventListener("click", function (ev) { ev.preventDefault(); draw(view); });
    });
  });

  routeButtons.forEach(function (b) {
    b.addEventListener("click", function () { draw(b.getAttribute("data-view")); });
  });

  // F34-T47: "Proved statements folded · unfold" in the figure's heading, for a route that folds
  // any: the route's layout with every fold open (<route>~open), and back.
  var foldsLine = document.querySelector(".figure-folds");
  var unfoldAll = foldsLine ? foldsLine.querySelector("button.unfold-all") : null;
  function figureFolds(to) {
    if (!foldsLine) { return; }
    var route = base(to), any = has(route + "~open");
    var open = any && to === route + "~open";
    foldsLine.hidden = !any;
    if (unfoldAll) {
      unfoldAll.textContent = open ? "fold" : "unfold";
      unfoldAll.setAttribute("aria-pressed", open ? "true" : "false");
    }
    if (foldsLine.firstChild && foldsLine.firstChild.nodeType === 3) {
      foldsLine.firstChild.nodeValue = open ? "Proved statements shown · " : "Proved statements folded · ";
    }
  }
  if (unfoldAll) {
    unfoldAll.addEventListener("click", function () {
      var route = base(state.view);
      if (!has(route + "~open")) { return; }
      transition(state.view === route + "~open" ? route : route + "~open");
    });
  }

  document.addEventListener("keydown", function (ev) {
    if (ev.key !== "Escape") { return; }
    // F34-T16 (R16): Esc comes back to the problem's own statement first, then to the home route
    if (homeNode && state.node !== homeNode) { select(homeNode); state.open = null; writeHash(); placePanel(); return; }
    if (state.view !== HOME) { transition(HOME); }
  });

  // F34-T55 (the owner, 2026-11-28): no control draws every statement in place of the selected
  // route; the statements on no route are a link to §2. The all layout stays, at its bookmark.

  // -- F34-T48 (ROUND-2 D2): "Show n harder routes" ------------------------------------------------
  // The quiet control under the picker swaps the picker for the one that also numbers the harder
  // routes, and shows their rows of the List. It never changes Figure 1 by itself; hiding them
  // while one is drawn comes back to the home route.
  var harderLink = document.querySelector("button.harder-link");
  var harderRows = document.querySelector(".harder-routes");
  var harderWords = { plain: "", shown: "" };
  function showHidden(el, hide) {
    if (!el) { return; }
    if (hide) { el.setAttribute("hidden", ""); } else { el.removeAttribute("hidden"); }
  }
  function showHarder(on) {
    if (!harderLink || !hardSelector) { return; }
    showHidden(selector, on);
    showHidden(hardSelector, !on);
    showHidden(harderRows, !on);
    routeButtons.forEach(function (b) { if (b.hasAttribute("data-harder")) { showHidden(b, !on); } });
    harderLink.setAttribute("aria-pressed", on ? "true" : "false");
    harderLink.textContent = on ? harderWords.shown : harderWords.plain;
    if (!on && base(state.view).indexOf(HARD) === 0) { transition(HOME); }
  }
  if (harderLink && hardSelector) {
    harderWords.plain = harderLink.textContent;
    harderWords.shown = harderLink.getAttribute("data-shown-label") || harderWords.plain;
    showHidden(harderLink.parentNode, false);
    harderLink.addEventListener("click", function () {
      showHarder(harderLink.getAttribute("aria-pressed") !== "true");
    });
  }

  // -- F27-R13: "Stop at proved statements" ---------------------------------------------------------

  function setFollow(on) {
    state.follow = !!on;
    if (followBox) { followBox.checked = !state.follow; }
    if (setsGrid) { setsGrid.classList.toggle("follow-proved", state.follow); }
    if (isSetView(state.view)) { transition(withMode(state.view)); }
    else { refreshLit(); }
  }

  if (followBox) {
    var followLabel = followBox.closest ? followBox.closest("label") : followBox.parentNode;
    if (followLabel) { followLabel.hidden = false; }
    followBox.addEventListener("change", function () { setFollow(!followBox.checked); });
  }

  // -- the start, and the hash ---------------------------------------------------------------------

  // -- F34-T17 (R17): on a phone, the selected route as an outline ----------------------------------

  var outline = document.querySelector("ol.route-outline");
  var phone = window.matchMedia ? window.matchMedia("(max-width: 760px)") : null;
  var panelHome = panels.length ? panels[0].parentNode : null;
  // F34-T56 (the owner, 2026-11-28): the outline folds what the drawing folds, and counts what
  // the drawing counts. Fold i of a route holds the statements its layout with that fold open
  // (<route>~fold<i>) draws and its own layout does not; the box is built here, before the first
  // of them, and opens in place. (The outline had a rule of its own over every route together,
  // so a phone said "10 proved statements" where the drawing said 3.)
  var foldOpen = {};
  function outlineFollows(view) {
    if (!outline || !layouts || !layouts[view]) { return; }
    var route = base(view), home = layouts[route] || layouts[view];
    var allOpen = view === route + "~open";
    slice(outline.querySelectorAll("li.fold")).forEach(function (li) { outline.removeChild(li); });
    var rows = slice(outline.children), foldOf = {}, folds = [];
    for (var i = 0; layouts[route + "~fold" + i]; i++) {
      folds.push({ key: route + ":" + i, rows: [], open: allOpen || view === route + "~fold" + i });
      rows.forEach(function (li) {
        var id = li.getAttribute("data-node");
        if (id && !nodeIn(home, id) && nodeIn(layouts[route + "~fold" + i], id) && foldOf[id] === undefined) {
          foldOf[id] = i;
          folds[i].rows.push(li);
        }
      });
    }
    rows.forEach(function (li) {
      var id = li.getAttribute("data-node");
      if (!id) { return; }
      var f = foldOf[id];
      if (f === undefined) { li.hidden = !nodeIn(home, id) && !nodeIn(layouts[view], id); return; }
      li.hidden = !(folds[f].open || foldOpen[folds[f].key]);
    });
    folds.forEach(function (f) {
      if (!f.rows.length || f.open) { return; }
      var li = document.createElement("li"), b = document.createElement("button");
      var depth = /depth-\d+/.exec(f.rows[0].className);
      li.className = "fold " + (depth ? depth[0] : "depth-1");
      b.type = "button";
      b.className = "fold-box";
      b.setAttribute("aria-expanded", foldOpen[f.key] ? "true" : "false");
      b.textContent = f.rows.length + " proved statements \u25B8";
      b.addEventListener("click", function () {
        foldOpen[f.key] = !foldOpen[f.key];
        outlineFollows(state.view);
      });
      li.appendChild(b);
      outline.insertBefore(li, f.rows[0]);
    });
  }
  function putBack() {
    panels.forEach(function (p) { if (p.parentNode !== panelHome && panelHome) { panelHome.appendChild(p); } });
    if (outline) { slice(outline.children).forEach(function (li) { li.classList.remove("selected"); }); }
  }
  // F34-T39 (REMINDERS item 22; layout B): on a phone the selected statement's record sits directly
  // under its row of the outline, from the start, after a tap and after a tap closes it again (the
  // problem's own record, under its own row); anywhere else it goes back beside the drawing.
  // F34-T51 (ROUND-2 D8): as the page opens no record is open, so the outline starts with the
  // problem's own row and runs on from it; a tapped row's record takes the row's place under its
  // dark header (the name shows once), and a tap on that header closes it.
  function placePanel() {
    putBack();
    var onPhone = !!(outline && phone && phone.matches);
    var id = onPhone ? state.open : null, li = null;
    if (id) {
      slice(outline.children).forEach(function (x) { if (x.getAttribute("data-node") === id) { li = x; } });
    }
    var panel = id ? panels.filter(function (p) { return p.getAttribute("data-node") === id; })[0] : null;
    var under = !!(li && !li.hidden && panel);
    if (under) { li.appendChild(panel); li.classList.add("selected"); }
    // beside the drawing there is nothing to show on a phone unless the open record has no row
    if (panelHome) { panelHome.classList.toggle("phone-closed", onPhone && (under || !id || !panel)); }
  }
  if (outline) {
    outline.addEventListener("click", function (ev) {
      if (!(phone && phone.matches) || !ev.target.closest) { return; }
      var head = ev.target.closest(".panel-head");
      if (head && outline.contains(head) && !ev.target.closest("a")) {
        state.open = null;
        if (homeNode) { select(homeNode); }
        writeHash();
        placePanel();
        return;
      }
      var a = ev.target.closest("a[data-node]");
      if (!a || a.parentNode.parentNode !== outline) { return; }
      ev.preventDefault();
      var id = a.getAttribute("data-node");
      if (select(id)) { state.open = id; }
      writeHash();
      placePanel();
    });
    if (phone && phone.addEventListener) { phone.addEventListener("change", placePanel); }
  }

  // -- F34-T37 (REMINDERS item 15): layout A — a line from the selected box to the panel ------------
  // Drawn over the drawing-and-panel grid whenever the panel stands beside the drawing (its left
  // edge right of the box): out from the box's right side, down or up beside the panel, into its
  // left edge. Hidden when the panel is under the statement (a phone) or the selection is not drawn.
  var linkGrid = document.querySelector(".graph-grid");
  var linkSvg = null;
  function drawLink() {
    if (!linkGrid) { return; }
    if (!linkSvg) {
      linkSvg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
      linkSvg.setAttribute("class", "panel-link");
      linkSvg.setAttribute("aria-hidden", "true");
      linkSvg.appendChild(document.createElementNS("http://www.w3.org/2000/svg", "path"));
      linkGrid.appendChild(linkSvg);
    }
    var g = svg.querySelector("g.node.selected");
    var panel = panels.filter(function (p) { return !p.hidden; })[0];
    var rect = g && !g.classList.contains("off-view") ? g.querySelector("rect.pill") : null;
    var inGrid = panel && panel.parentNode && panel.parentNode.classList.contains("panels");
    if (!rect || !inGrid) { linkSvg.style.display = "none"; return; }
    var gr = linkGrid.getBoundingClientRect(), a = rect.getBoundingClientRect();
    var b = panel.getBoundingClientRect();
    if (!a.width || b.left < a.right + 16) { linkSvg.style.display = "none"; return; }
    var x0 = a.right - gr.left, y0 = a.top + a.height / 2 - gr.top;
    var x2 = b.left - gr.left;
    var y2 = Math.min(Math.max(y0, b.top - gr.top + 30), b.bottom - gr.top - 30);
    var xm = x2 - 14;
    linkSvg.style.display = "";
    linkSvg.setAttribute("width", String(Math.ceil(gr.width)));
    linkSvg.setAttribute("height", String(Math.ceil(gr.height)));
    linkSvg.firstChild.setAttribute("d", "M" + x0 + " " + y0 + "H" + xm + "V" + y2 + "H" + x2);
  }
  var linkQueued = false;
  function queueLink() {
    if (linkQueued) { return; }
    linkQueued = true;
    window.requestAnimationFrame(function () { linkQueued = false; drawLink(); });
  }
  window.addEventListener("scroll", queueLink, { passive: true });
  window.addEventListener("resize", queueLink);
  queueLink();

  // -- F34-T36 (REMINDERS item 16): a statement in "Not on a route" selects too -----------------------
  // Its line in a group's list, or its box in the group's small tree, selects it into the same
  // panel as a statement of the drawing and brings the panel into view; the page stays. Without the
  // script, or for a statement with no panel here, the link goes to the statement's own page.
  var offRoute = document.querySelector("section.off-route");
  if (offRoute) {
    offRoute.addEventListener("click", function (ev) {
      var t = ev.target;
      if (!t.closest) { return; }
      var box = t.closest("svg.mini-tree g.node[data-node]");
      var li = box ? null : t.closest("li[data-node]");
      if (li && t.closest("a") !== li.querySelector("a")) { return; }  // "replaced by" stays a link
      var id = box ? box.getAttribute("data-node") : (li ? li.getAttribute("data-node") : null);
      var panel = id ? panels.filter(function (p) { return p.getAttribute("data-node") === id; })[0] : null;
      if (!panel) { return; }
      ev.preventDefault();
      select(id);
      state.open = id;
      writeHash();
      placePanel();  // F34-T39: under its outline row on a phone, if the route draws it
      panel.scrollIntoView({ block: "start" });
    });
  }

  // -- F34-T49 (ROUND-2 D7): "also used by Route n" in §2 draws that route ---------------------------
  slice(document.querySelectorAll("a.route-ref")).forEach(function (a) {
    a.addEventListener("click", function (ev) {
      var m = /view=([^&]+)/.exec(a.getAttribute("href") || "");
      var view = m ? decodeURIComponent(m[1]) : null;
      if (!has(view)) { return; }
      ev.preventDefault();
      if (base(view).indexOf(HARD) === 0) { showHarder(true); }
      draw(view);
      var figure = document.getElementById("proof");
      if (figure) { figure.scrollIntoView({ block: "start" }); }
    });
  });

  // -- F34-T12 (R14): Tree and List -----------------------------------------------------------------

  var tabs = document.querySelector(".route-tabs");
  if (tabs) {
    var tabButtons = slice(tabs.querySelectorAll("button[role=tab]"));
    var panesOf = {};
    tabButtons.forEach(function (b) {
      panesOf[b.getAttribute("aria-controls")] = document.getElementById(b.getAttribute("aria-controls"));
    });
    var showRouteTab = function (id) {
      tabButtons.forEach(function (b) {
        var on = b.getAttribute("aria-controls") === id;
        b.setAttribute("aria-selected", on ? "true" : "false");
        if (panesOf[b.getAttribute("aria-controls")]) { panesOf[b.getAttribute("aria-controls")].hidden = !on; }
      });
    };
    tabButtons.forEach(function (b) {
      b.addEventListener("click", function () { showRouteTab(b.getAttribute("aria-controls")); });
    });
    showRouteTab("sets-tree");
    tabs.hidden = false;
  }

  var initial = fromHash();
  if (initial.view && initial.view.indexOf(FOLLOW) === 0 && has(initial.view)) {
    state.follow = true;
    if (followBox) { followBox.checked = false; }
    if (setsGrid) { setsGrid.classList.add("follow-proved"); }
  }
  if (!select(initial.node || (panels.length ? panels[0].getAttribute("data-node") : null)) && panels.length) {
    select(panels[0].getAttribute("data-node"));
  }
  if (initial.node && initial.node === state.node) { state.open = initial.node; }  // a bookmarked record
  if (initial.band && pillOf(bandSvg, initial.band)) { state.band = initial.band; }
  var opening = has(initial.view) ? initial.view : (has(HOME) ? HOME : null);
  if (opening && base(opening).indexOf(HARD) === 0) { showHarder(true); }
  if (opening && opening !== state.view) {
    transition(opening, true);
  } else if (has(state.view)) {
    settle(state.view, true);
  }
  // F04-T18: a panel's "Superseded by" link is an in-page #node= link, so the hash can change
  // without a pill being clicked.
  window.addEventListener("hashchange", function () {
    var h = fromHash();
    if (h.node) { if (select(h.node)) { state.open = h.node; } placePanel(); }
    var view = h.view || HOME;
    if (has(view) && view !== state.view) {
      if (isSetView(view) && (view.indexOf(FOLLOW) === 0) !== state.follow) { setFollow(view.indexOf(FOLLOW) === 0); }
      transition(view);
    }
  });
})();
