// My problems (F23-T9; R13; D-36 v3.33). /me/ is a static shell: for every problem, the sections
// of its words that wait for a steward's or curator's approval are already in the page, hidden,
// rendered from the same products as the problem pages. Once session.js has the service's answer
// this shows the signed-in login's roles, the waiting sections of each problem they steward, their
// own open pull requests (the service's public GET /submissions.json, kept to their pseudonym) and
// Step down per problem. Signed out it offers Sign in; with the service down it shows nothing more
// than the shell (C7). Everything from the service is set as text.
(function () {
  "use strict";
  var root = document.querySelector(".me[data-me]");
  if (!root || !window.OPN) { return; }
  var O = window.OPN;
  var el = O.el;
  var pulls = (root.dataset.repo || "").replace(/\/+$/, "") + "/pull/";

  function section(title) {
    var s = el("section", { "class": "me-section" });
    s.appendChild(el("h2", {}, title));
    root.appendChild(s);
    return s;
  }

  function stepDown(li, target, login) {
    var out = el("span", { "class": "form-error", role: "alert" });
    var b = el("button", { type: "button", "class": "btn btn-ghost" }, "Step down");
    b.addEventListener("click", function () {
      b.disabled = true;
      O.call("POST", "/stewards", {
        target: target, action: "step-down", name: login, link: null, accept: true
      }).then(function (r) {
        if (r.status === 201) {
          li.removeChild(b);
          var p = el("span", { "class": "receipt" }, " Step-down filed: ");
          if (r.data && typeof r.data.pr_url === "string" && r.data.pr_url.indexOf(pulls) === 0) {
            p.appendChild(el("a", { href: r.data.pr_url }, "#" + String(r.data.pr_number)));
          }
          li.appendChild(p);
          return;
        }
        out.textContent = O.errorText(r);
        b.disabled = false;
      }, function () { out.textContent = O.errorText(null); b.disabled = false; });
    });
    li.appendChild(b);
    li.appendChild(out);
  }

  O.session.then(function (s) {
    var intro = root.querySelector(".me-intro");
    if (!s.signed_in) {
      root.appendChild(el("a", { "class": "btn btn-primary", href: O.signInHref("/me/") },
        "Sign in with GitHub"));
      return;
    }
    if (intro) { intro.hidden = true; }
    var roles = ["signed in as " + s.login];
    if (s.curator) { roles.push("curator"); }
    roles.push(s.stewards.length ? "steward of " + s.stewards.join(", ") : "steward of no problem yet");
    root.appendChild(el("p", { "class": "lead me-roles" }, roles.join(" · ")));

    var mine = section("Problems you steward");
    if (!s.stewards.length) {
      var p = el("p", { "class": "cue" }, "None yet. ");
      p.appendChild(el("a", { href: "/steward/" }, "Problems that need a steward →"));
      mine.appendChild(p);
    }
    s.stewards.forEach(function (target) {
      var head = el("h3", {});
      head.appendChild(el("a", { href: "/problems/" + encodeURIComponent(target) + "/" }, target));
      mine.appendChild(head);
      var waiting = root.querySelector('.waiting[data-target="' + target.replace(/[^a-z0-9-]/g, "") + '"]');
      if (waiting) {
        waiting.hidden = false;
        mine.appendChild(waiting);
      } else {
        mine.appendChild(el("p", { "class": "cue" }, "Nothing waits for your approval."));
      }
      var li = el("p", { "class": "me-step-down" });
      stepDown(li, target, s.login);
      mine.appendChild(li);
    });

    var prs = section("Your open pull requests");
    var list = el("ul", { "class": "me-prs" });
    prs.appendChild(list);
    // The public listing, read as in-review.js reads it: no credentials, filtered here.
    fetch(O.api + "/submissions.json", { credentials: "omit" }).then(function (resp) {
      return resp.json().then(function (d) { return { ok: resp.ok, status: resp.status, data: d }; },
        function () { return { ok: false, status: resp.status, data: null }; });
    }).then(function (r) {
      var open = r.ok && r.data && Array.isArray(r.data.open) ? r.data.open : null;
      if (!open) { prs.appendChild(el("p", { "class": "cue" }, O.errorText(r))); return; }
      var who = String(s.pseudonym || s.login).toLowerCase();
      var own = open.filter(function (e) { return e && String(e.pseudonym || "").toLowerCase() === who; });
      if (!own.length) { prs.appendChild(el("p", { "class": "cue" }, "None open.")); return; }
      own.forEach(function (e) {
        var item = el("li", {});
        var number = "#" + String(e.pr_number);
        if (typeof e.pr_url === "string" && pulls !== "/pull/" && e.pr_url.indexOf(pulls) === 0) {
          item.appendChild(el("a", { href: e.pr_url }, number));
        } else { item.appendChild(document.createTextNode(number)); }
        item.appendChild(document.createTextNode(" · " + String(e.kind || "") +
          (e.node_id ? " on " + String(e.node_id) : e.target_id ? " on " + String(e.target_id) : "")));
        list.appendChild(item);
      });
    }, function () { prs.appendChild(el("p", { "class": "cue" }, O.errorText(null))); });
  }).catch(function () { /* the shell stays as rendered */ });
})();
