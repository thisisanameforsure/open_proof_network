// Docs search (F34-T10, Q13; handoff §3.3). Every Docs page carries the search box hidden; this
// shows it and, on first use, loads the index the build wrote (/docs/search-index.js, a
// same-origin script, since the site's policy lets a page connect only to the service). A query
// finds the pages that hold every word, the page titled by a word first, each linked to the
// heading that matched; nothing found says so. Without the script the sidebar is the way round.
(function () {
  "use strict";
  var form = document.querySelector(".docs-search");
  if (!form) { return; }
  var input = form.querySelector("input[type=search]");
  var out = form.querySelector(".docs-results");
  var loading = null;

  function load() {
    if (window.OPN_DOCS_INDEX) { return Promise.resolve(window.OPN_DOCS_INDEX.pages); }
    if (!loading) {
      loading = new Promise(function (resolve) {
        var s = document.createElement("script");
        s.src = "/docs/search-index.js";
        s.onload = function () { resolve((window.OPN_DOCS_INDEX || { pages: [] }).pages); };
        s.onerror = function () { resolve([]); };
        document.head.appendChild(s);
      });
    }
    return loading;
  }

  function has(hay, w) { return hay.toLowerCase().indexOf(w) !== -1; }

  function score(page, words) {
    var total = 0, best = null;
    for (var i = 0; i < words.length; i++) {
      var w = words[i], hit = false;
      if (has(page.title, w)) { total += 10; hit = true; }
      for (var j = 0; j < page.headings.length; j++) {
        if (has(page.headings[j].text, w)) { total += 3; hit = true; if (!best) { best = page.headings[j]; } }
      }
      if (has(page.text, w)) { total += 1; hit = true; }
      if (!hit) { return null; }
    }
    return { page: page, score: total, heading: best };
  }

  function snippet(text, word) {
    var at = text.toLowerCase().indexOf(word);
    if (at < 0) { return text.slice(0, 120); }
    var from = Math.max(0, at - 50);
    return (from ? "…" : "") + text.slice(from, at + 90) + "…";
  }

  function show(query) {
    var words = query.toLowerCase().split(/\s+/).filter(Boolean);
    out.textContent = "";
    if (!words.length) { return; }
    load().then(function (pages) {
      if (input.value !== query) { return; }  // a later keystroke owns the list
      var found = pages.map(function (p) { return score(p, words); })
        .filter(Boolean)
        .sort(function (a, b) { return b.score - a.score; })
        .slice(0, 8);
      out.textContent = "";
      if (!found.length) {
        var none = document.createElement("li");
        none.className = "cue";
        none.textContent = "No page holds every word of that.";
        out.appendChild(none);
        return;
      }
      found.forEach(function (f) {
        var li = document.createElement("li");
        var a = document.createElement("a");
        a.href = f.page.href + (f.heading ? "#" + f.heading.id : "");
        a.textContent = f.page.title + (f.heading ? " › " + f.heading.text : "");
        var p = document.createElement("p");
        p.className = "cue";
        p.textContent = snippet(f.page.text, words[0]);
        li.appendChild(a);
        li.appendChild(p);
        out.appendChild(li);
      });
    });
  }

  input.addEventListener("input", function () { show(input.value); });
  input.addEventListener("focus", function () { load(); }, { once: true });
  form.hidden = false;
})();
