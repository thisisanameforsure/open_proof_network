// Shelve, unshelve or retire from the site (F31-T11; D-14 v3.47). A page is static: a
// statement's page carries one hidden .shelve-act[data-target] slot with the node and, when it is
// shelved, who shelved it, when and why; the problem page carries one hidden
// .retire-act[data-target][data-node][data-partial][data-route][data-holes] per drawn route.
// Only once session.js has the service's answer does this offer a control, and only to a
// signed-in steward of the target or a curator: Shelve opens a small form for the cause and posts
// {node_id, action: "shelved", scope: "node", route: null, cause} to POST /shelvings; Unshelve
// posts the same with action "unshelved"; Retire posts scope "route" with the partial's path.
// Signed out, or with the service down, no control is drawn (C7). Every answer is set as text;
// nothing a person wrote is read back into markup.
//
// F31-T17: a filed record is followed until the page is drawn with it. The record takes about a
// quarter of an hour to reach the page (checked, merged, the products rendered, the site
// published), and until then the page is exactly as it was, which read as "nothing happened".
// So on 201 the filing is remembered in this browser (localStorage "opn.shelvings": the pull
// request, the node, the scope, the route; nothing a person wrote), and in place of the control
// the slot shows where the record is — Filed, Checked, Merged, On this page — from
// GET /submissions/{n}, asked again on a slow clock and whenever the tab is looked at. "On this
// page" is decided by the page itself: a fresh copy of this address is fetched and must show
// the change; then the note offers a reload and the next load forgets the filing. Meanwhile the
// drawing marks what the record will change with the class act-pending (the route's junction
// and holes, or the statement's pill). Nothing is ever drawn as shelved before the render says
// so: the check may still refuse the record. A viewer who did not file it is told a shelving
// record on the statement is pending, from GET /submissions.json (open and awaiting_render),
// whose rows do not say which route, so that note claims no more than the statement.
(function () {
  "use strict";
  var me = document.currentScript;
  if (!window.OPN) { return; }
  var O = window.OPN;
  var el = O.el;
  var pulls = ((me && me.dataset.repo) || "").replace(/\/+$/, "") + "/pull/";
  var slice = function (list) { return Array.prototype.slice.call(list); };

  var KEY = "opn.shelvings";
  var KEEP_MS = 48 * 3600 * 1000;       // a filing nobody came back to is forgotten
  var SETTLED_MS = 10 * 60 * 1000;      // rendered this long and the slot still stands: see drawn()
  var OPEN_MS = 10000, MERGED_MS = 30000;
  var STEPS = ["Filed", "Checked", "Merged", "On this page"];

  // --- the filings this browser remembers ---------------------------------------------------
  var memory = null;
  function load() {
    if (memory) { return memory; }
    var raw = [];
    try { raw = JSON.parse(window.localStorage.getItem(KEY) || "[]"); } catch (e) { raw = []; }
    var now = Date.now();
    memory = (Array.isArray(raw) ? raw : []).filter(function (e) {
      return e && typeof e.pr === "number" && typeof e.node === "string" &&
        typeof e.at === "number" && now - e.at < KEEP_MS;
    });
    return memory;
  }
  function save() {
    try { window.localStorage.setItem(KEY, JSON.stringify(memory || [])); } catch (e) { /* kept for this page only */ }
  }
  function forget(entry) {
    memory = load().filter(function (e) { return e.pr !== entry.pr; });
    save();
  }

  // --- the slots and the drawing ------------------------------------------------------------
  function slotsFor(entry, doc) {
    var sel = entry.scope === "route" ? ".retire-act[data-target]" : ".shelve-act[data-target]";
    return slice((doc || document).querySelectorAll(sel)).filter(function (s) {
      return s.dataset.target === entry.target && s.dataset.node === entry.node &&
        (entry.scope !== "route" || s.dataset.partial === entry.route);
    });
  }

  // Does `doc` (this page, or a fresh copy of it) already show what the record does?
  function shows(entry, doc) {
    var slots = slotsFor(entry, doc);
    if (entry.scope === "route") { return slots.length === 0; }  // a retired route offers no Retire
    return slots.length > 0 &&
      slots[0].dataset.shelved === (entry.action === "shelved" ? "1" : "0");
  }

  function mark(nodes, routes, on, words) {
    slice(document.querySelectorAll("svg g.node[data-node], svg g.junction[data-route]")).forEach(function (g) {
      var hit = g.classList.contains("junction")
        ? routes.indexOf(g.getAttribute("data-route")) >= 0
        : nodes.indexOf(g.getAttribute("data-node")) >= 0;
      if (!hit) { return; }
      g.classList.toggle("act-pending", on);
      var title = g.querySelector("title");
      if (!title) { return; }
      if (g.dataset.plainTitle === undefined) { g.dataset.plainTitle = title.textContent; }
      title.textContent = on ? g.dataset.plainTitle + "; " + words : g.dataset.plainTitle;
    });
  }
  function markEntry(entry, on) {
    var words = noun(entry).toLowerCase() + " pending (#" + String(entry.pr) + ")";
    if (entry.scope !== "route") { mark([entry.node], [], on, words); return; }
    slotsFor(entry).slice(0, 1).forEach(function (s) {
      var holes = (s.dataset.holes || "").split(" ").filter(Boolean);
      mark(holes, s.dataset.route ? [s.dataset.route] : [], on, words);
    });
  }

  function noun(entry) {
    if (entry.scope === "route") { return "Retirement"; }
    return entry.action === "unshelved" ? "Unshelving" : "Shelving";
  }

  function prLink(number, url) {
    var text = "#" + String(number);
    if (typeof url === "string" && pulls !== "/pull/" && url.indexOf(pulls) === 0) {
      return el("a", { href: url }, text);
    }
    return document.createTextNode(text);
  }

  // --- one filed record, followed -----------------------------------------------------------
  // state -> [the step in progress (4: none left), the words]
  var WORDS = {
    checking: [1, "The gate is checking the record, which takes about a minute."],
    merging: [2, "Checked. It merges next, usually within a minute or two."],
    review: [2, "Checked. It waits for a review before it can merge."],
    failed: [1, "The check refused the record; the pull request says why. Nothing has changed."],
    rendering: [3, "Merged: it is on the record. This page is redrawn when the next render lands, usually about a quarter of an hour after the merge. You can leave; this note stays until the page shows it."],
    publishing: [3, "Merged and rendered. The site is publishing the new page."],
    drawn: [4, "The page has been redrawn with it."],
    refused: [1, "The pull request was closed without merging. Nothing has changed."]
  };

  function follow(entry) {
    var hosts = slotsFor(entry);
    if (!hosts.length) { return; }
    var state = null, timer = null, busy = false, over = false;
    var boxes = hosts.map(function (host) {
      slice(host.childNodes).forEach(function (c) { host.removeChild(c); });  // the control, if drawn
      var box = el("div", { "class": "act-progress", role: "status" });
      var head = el("p", { "class": "receipt act-head" });
      head.appendChild(el("strong", {}, noun(entry) + " filed"));
      head.appendChild(document.createTextNode(" as "));
      head.appendChild(prLink(entry.pr, entry.url));
      head.appendChild(document.createTextNode("."));
      box.appendChild(head);
      var list = el("ol", { "class": "act-steps" });
      STEPS.forEach(function (s) { list.appendChild(el("li", {}, s)); });
      box.appendChild(list);
      box.appendChild(el("p", { "class": "cue act-words" }));
      host.appendChild(box);
      host.hidden = false;
      host.dataset.following = "1";
      var fold = host.closest ? host.closest("details") : null;
      if (fold) { fold.open = true; }
      return box;
    });

    function show(next) {
      if (next === state) { return; }
      state = next;
      var at = WORDS[state][0];
      boxes.forEach(function (box) {
        box.dataset.state = state;
        slice(box.querySelectorAll(".act-steps li")).forEach(function (li, i) {
          li.className = i < at ? "done" : (i === at ? "now" : "");
          if (i === at && (state === "failed" || state === "refused")) { li.className = "now bad"; }
        });
        box.querySelector(".act-words").textContent = WORDS[state][1];
        slice(box.querySelectorAll("button")).forEach(function (b) { box.removeChild(b); });
        if (state === "drawn") {
          var reload = el("button", { type: "button", "class": "btn btn-secondary btn-small act-reload" }, "Reload to see it");
          reload.addEventListener("click", function () { window.location.reload(); });
          box.appendChild(reload);
        }
        if (state === "failed" || state === "refused") {
          var dismiss = el("button", { type: "button", "class": "btn btn-ghost btn-small act-dismiss" }, "Dismiss");
          dismiss.addEventListener("click", function () {
            over = true;
            window.clearTimeout(timer);
            forget(entry);
            markEntry(entry, false);
            hosts.forEach(function (host) {
              slice(host.childNodes).forEach(function (c) { host.removeChild(c); });
              delete host.dataset.following;
            });
            offer();  // the control again, for whoever may use it
          });
          box.appendChild(dismiss);
        }
      });
      markEntry(entry, state !== "drawn" && state !== "refused");
      if (state === "drawn" || state === "refused") { over = true; }
    }

    // A fresh copy of this very page: does it show the change yet?
    function fresh() {
      return fetch(window.location.pathname, { cache: "reload", credentials: "omit" }).then(function (resp) {
        if (!resp.ok) { return false; }
        return resp.text().then(function (text) {
          var doc = new DOMParser().parseFromString(text, "text/html");
          if (!doc.querySelector("main")) { return false; }
          if (shows(entry, doc)) { return true; }
          // A retired route may keep a hole another route needs, and then its Retire control
          // stays: once the render has been out a while, the page is as drawn as it will be.
          return typeof entry.rendered === "number" && Date.now() - entry.rendered > SETTLED_MS;
        });
      }, function () { return false; });
    }

    function ask() {
      if (over || busy || document.hidden) { return; }
      busy = true;
      fetch(O.api + "/submissions/" + String(entry.pr), { credentials: "omit" }).then(function (resp) {
        return resp.ok ? resp.json() : null;
      }).then(function (d) {
        var pr = d && d.pull_request;
        if (!pr) { return; }                               // no answer: what is shown stands
        if (pr.merged) {
          if (pr.waiting_on === "products") { show("rendering"); return; }
          if (typeof entry.rendered !== "number") { entry.rendered = Date.now(); save(); }
          return fresh().then(function (yes) { show(yes ? "drawn" : "publishing"); });
        }
        if (pr.state === "closed") { show("refused"); return; }
        var w = pr.waiting_on;
        show(w === "merge" || w === "branch-update" ? "merging"
          : w === "step9-review" ? "review"
          : w === "gate-failed" || w === "conflict" ? "failed" : "checking");
      }).catch(function () { /* what is shown stands */ }).then(function () {
        busy = false;
        if (over) { return; }
        window.clearTimeout(timer);
        timer = window.setTimeout(ask, state === "rendering" || state === "publishing" ? MERGED_MS : OPEN_MS);
      });
    }

    show("checking");
    ask();
    window.addEventListener("focus", ask);
    document.addEventListener("visibilitychange", ask);
  }

  // --- the controls -------------------------------------------------------------------------
  function post(host, body, controls, out) {
    controls.forEach(function (c) { c.disabled = true; });
    O.call("POST", "/shelvings", body).then(function (r) {
      if (r.status === 201 && r.data && typeof r.data.pr_number === "number") {
        var entry = {
          pr: r.data.pr_number,
          url: typeof r.data.pr_url === "string" ? r.data.pr_url : "",
          target: host.dataset.target,
          node: body.node_id,
          scope: body.scope,
          route: body.route,
          action: body.action,
          at: Date.now(),
          path: window.location.pathname
        };
        load().push(entry);
        save();
        follow(entry);
        return;
      }
      out.textContent = O.errorText(r);
      controls.forEach(function (c) { c.disabled = false; });
    }, function () {
      out.textContent = O.errorText(null);
      controls.forEach(function (c) { c.disabled = false; });
    });
  }

  // One control: a button that opens a form for the cause, and a send that posts `shape(cause)`.
  function control(host, label, cue, shape) {
    var out = el("span", { "class": "form-error", role: "alert" });
    var b = el("button", { type: "button", "class": "btn btn-ghost btn-small" }, label);
    b.addEventListener("click", function () {
      if (host.querySelector(".shelve-form")) { return; }
      var form = el("div", { "class": "shelve-form ctl-box" });
      form.appendChild(el("p", { "class": "cue" }, cue));
      var cause = el("textarea", { "class": "input", name: "cause", "aria-label": "Your reasoning, published with the record" });
      cause.placeholder = "Why, in your words (published with the record)";
      var send = el("button", { type: "button", "class": "btn btn-secondary btn-small send" }, "File it");
      var cancel = el("button", { type: "button", "class": "btn btn-ghost btn-small" }, "Cancel");
      send.addEventListener("click", function () {
        var words = cause.value.trim();
        if (!words) { out.textContent = "Write the cause first."; return; }
        if (words.length > 1000) { out.textContent = "A cause is at most 1000 characters."; return; }
        out.textContent = "";
        post(host, shape(words), slice(host.querySelectorAll("button")), out);
      });
      cancel.addEventListener("click", function () { host.removeChild(form); out.textContent = ""; });
      form.appendChild(cause);
      form.appendChild(send);
      form.appendChild(cancel);
      host.appendChild(form);
    });
    host.appendChild(document.createTextNode(" "));
    host.appendChild(b);
    host.appendChild(out);
  }

  var act = document.querySelector(".shelve-act[data-target]");
  var retires = slice(document.querySelectorAll(".retire-act[data-target]"));
  if (!act && !retires.length) { return; }
  var slots = (act ? [act] : []).concat(retires);

  // The controls, for a steward of the target or a curator; never in a slot that is following a
  // filed record, and never twice in one slot.
  function offer() {
    O.session.then(function (s) {
      if (!s.signed_in) { return; }
      function allowed(target) { return s.curator || s.stewards.indexOf(target) >= 0; }
      function free(host) {
        return allowed(host.dataset.target) && !host.dataset.following && !host.querySelector("button");
      }
      if (act && free(act)) {
        var node = act.dataset.node;
        if (act.dataset.shelved === "1") {
          control(act, "Unshelve",
            "Lift the shelving with a record of your own; the earlier record stays on the record as history.",
            function (cause) { return { node_id: node, action: "unshelved", scope: "node", route: null, cause: cause }; });
        } else {
          control(act, "Shelve",
            "Shelve this statement and every hole beneath it: off the frontier, work refused, hidden from the routes view, until an unshelve record lifts it (D-14 v3.47).",
            function (cause) { return { node_id: node, action: "shelved", scope: "node", route: null, cause: cause }; });
        }
        act.hidden = false;
      }
      retires.forEach(function (r) {
        if (!free(r)) { return; }
        var node = r.dataset.node;
        var partial = r.dataset.partial;
        control(r, "Retire this route",
          "Retire this decomposition: its holes leave the frontier and the drawing; the statement it sits on is untouched (D-14 v3.47).",
          function (cause) { return { node_id: node, action: "shelved", scope: "route", route: partial, cause: cause }; });
        r.hidden = false;
      });
    }).catch(function () { /* no session: the page stays read-only */ });
  }

  // The filings this browser remembers: one the page already shows is forgotten; one that
  // belongs to a slot here is followed in it.
  var mine = {};
  load().slice().forEach(function (entry) {
    var home = entry.path === window.location.pathname;
    var here = slotsFor(entry).length > 0;
    if ((home || here) && shows(entry, document)) { forget(entry); return; }
    mine[entry.pr] = true;
    if (here) { follow(entry); } else { markEntry(entry, true); }
  });
  offer();

  // What anybody has pending on these statements, from the public listing.
  var targets = [];
  slots.forEach(function (s) { if (targets.indexOf(s.dataset.target) < 0) { targets.push(s.dataset.target); } });
  targets.forEach(function (target) {
    var url = O.api + "/submissions.json?target=" + encodeURIComponent(target) + "&kind=shelving";
    fetch(url, { credentials: "omit" }).then(function (resp) {
      return resp.ok ? resp.json() : null;
    }).then(function (listing) {
      if (!listing) { return; }
      [["open", "in review"], ["awaiting_render", "merged and not drawn yet"]].forEach(function (pair) {
        (Array.isArray(listing[pair[0]]) ? listing[pair[0]] : []).forEach(function (e) {
          if (!e || e.kind !== "shelving" || e.target_id !== target) { return; }
          if (typeof e.pr_number !== "number" || mine[e.pr_number]) { return; }
          slots.forEach(function (s) {
            if (s.dataset.target !== target || s.dataset.node !== e.node_id) { return; }
            var note = el("p", { "class": "cue act-others" });
            note.appendChild(document.createTextNode("A shelving record on this statement is " + pair[1] + ": "));
            note.appendChild(prLink(e.pr_number, e.pr_url));
            note.appendChild(document.createTextNode(" by " + String(e.pseudonym || "someone") + "."));
            s.appendChild(note);
          });
          mark([e.node_id], [], true, "shelving record pending (#" + String(e.pr_number) + ")");
        });
      });
    }).catch(function () { /* the page stays as rendered */ });
  });
})();
